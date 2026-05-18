export default {
  async email(message, env, ctx) {
    if (!message.headers.get("from")?.endsWith(`<no-reply@${env.EMAIL_DOMAIN.toLowerCase()}>`) || message.headers.get("subject") != `=?utf-8?Q?Your=20${env.EMAIL_DOMAIN}=20Login=20Code?=`) return;

    const raw = await new Response(message.raw).text();

    const code = raw.match(/\b\d{6}\b/)?.[0];
    if (!code) return;
    console.log("Extracted login code:", code);

    try {
      const res = await env.VPC_SERVICE.fetch(
        "http://backend/api/login-code/",
        {
          method: "POST",
          headers: {
            "content-type": "application/json",
            "X-Email-Worker-Secret": env.api_auth_token,
          },
          body: JSON.stringify({
            email: message.to,
            code,
          }),
        }
      );

      const text = await res.text().catch(() => "");

      console.log("Login code POST result:", {
        ok: res.ok,
        status: res.status,
        response: text,
      });
    } catch (err) {
      console.error("Login code POST failed:", err);
    }
  }
};