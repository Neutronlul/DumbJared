from django.shortcuts import render
from rest_framework import viewsets
from api.models import Team, Glossary
from api.serializers import TeamSerializer, GlossarySerializer


# Create your views here.
class TeamViewSet(viewsets.ModelViewSet):
    queryset = Team.objects.all()
    serializer_class = TeamSerializer


class GlossaryViewSet(viewsets.ModelViewSet):
    queryset = Glossary.objects.all()
    serializer_class = GlossarySerializer
