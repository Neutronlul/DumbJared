from rest_framework import serializers

from api.models import Glossary, Team, TeamName


class TeamNameSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = TeamName
        fields = ("name",)


class TeamSerializer(serializers.HyperlinkedModelSerializer):
    names = TeamNameSerializer(many=True, read_only=True)

    class Meta:
        model = Team
        fields = ("team_id", "names")


class GlossarySerializer(serializers.HyperlinkedModelSerializer):
    entry = serializers.SerializerMethodField()

    class Meta:
        model = Glossary
        fields = ("entry",)

    def get_entry(self, obj: Glossary) -> str:
        return f"{obj.acronym} | {obj.definition}"
