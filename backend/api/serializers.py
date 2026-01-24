from api.models import Team, Glossary, TeamName

from rest_framework import serializers


class TeamNameSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = TeamName
        fields = ["name"]


class TeamSerializer(serializers.HyperlinkedModelSerializer):
    names = TeamNameSerializer(many=True, read_only=True)

    class Meta:
        model = Team
        fields = ["team_id", "names"]


class GlossarySerializer(serializers.HyperlinkedModelSerializer):
    entry = serializers.SerializerMethodField()

    class Meta:
        model = Glossary
        fields = ["entry"]

    def get_entry(self, obj):
        return f"{obj.acronym} | {obj.definition}"
