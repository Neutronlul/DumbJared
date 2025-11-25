from api.models import Team, Glossary

from rest_framework import serializers


class TeamSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Team
        fields = ["name"]


class GlossarySerializer(serializers.HyperlinkedModelSerializer):
    entry = serializers.SerializerMethodField()

    class Meta:
        model = Glossary
        fields = ["entry"]

    def get_entry(self, obj):
        return f"{obj.acronym} | {obj.definition}"
