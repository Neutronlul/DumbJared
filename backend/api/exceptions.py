class TeamHasNoNamesError(ValueError):
    def __init__(self) -> None:
        super().__init__("Team has no associated names")
