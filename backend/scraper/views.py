import hmac
import json
from http import HTTPStatus

from django.conf import settings
from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from redis import Redis

_redis_client: dict[str, Redis] = {}


def _redis() -> Redis:
    if "client" not in _redis_client:
        _redis_client["client"] = Redis.from_url(settings.REDIS_URL)
    return _redis_client["client"]

@csrf_exempt
@require_POST
def receive_login_code(request: HttpRequest) -> JsonResponse:
    """Handle POSTed login codes from the email worker and persist them to Redis.

    Expects a JSON body with 'email' and 'code', and a header
    'X-Email-Worker-Secret' that matches settings.WRANGLER_KEY. If a
    login attempt is currently tracked for the given email (a Redis
    lock key exists), the code is pushed into a Redis list and given a short
    TTL. Returns a JSON response indicating success or the appropriate
    error (bad request or unauthorized).

    Args:
        request: Django HttpRequest with JSON payload and header.

    Returns:
        JsonResponse: {'ok': True} on success, or {'error': ...} with
        HTTP 400/401 on failure.

    """
    if not settings.WRANGLER_KEY:
        return JsonResponse(
            {"error": "Wrangler key not set"},
            status=HTTPStatus.UNAUTHORIZED,
        )

    # The reason for doing this instead of a string equality check is
    # to prevent timing attacks, which is complete overkill but whatever
    if not hmac.compare_digest(
        request.headers.get("X-Email-Worker-Secret", ""),
        settings.WRANGLER_KEY,
    ):
        return JsonResponse({"error": "Unauthorized"}, status=HTTPStatus.UNAUTHORIZED)

    try:
        data = json.loads(request.body)
        code = data["code"]
        email = data["email"].lower()
    except json.JSONDecodeError, KeyError:
        return JsonResponse({"error": "Bad request"}, status=HTTPStatus.BAD_REQUEST)

    if not _redis().exists(f":1:login_lock:{email}"):
        return JsonResponse(
            {"error": "No login attempt in progress for this email"},
            status=HTTPStatus.BAD_REQUEST,
        )

    with _redis().pipeline() as pipe:
        pipe.lpush(f":1:login_code:{email}", code)
        pipe.expire(f":1:login_code:{email}", 30)
        pipe.execute()

    return JsonResponse({"ok": True})
