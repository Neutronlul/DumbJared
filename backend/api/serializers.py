from typing import ClassVar

from rest_framework import serializers

from api.models import Glossary, Team, TeamName


class TeamNameSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = TeamName
        fields: ClassVar[list] = ["name"]


class TeamSerializer(serializers.HyperlinkedModelSerializer):
    names = TeamNameSerializer(many=True, read_only=True)

    class Meta:
        model = Team
        fields: ClassVar[list] = ["team_id", "names"]


class GlossarySerializer(serializers.HyperlinkedModelSerializer):
    entry = serializers.SerializerMethodField()

    class Meta:
        model = Glossary
        fields: ClassVar[list] = ["entry"]

    def get_entry(self, obj: Glossary) -> str:
        return f"{obj.acronym} | {obj.definition}"
