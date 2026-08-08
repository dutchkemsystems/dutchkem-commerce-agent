"""Team features — roles, projects, and shared memory for enterprise teams."""

from typing import Dict, List, Optional


class TeamMember:
    def __init__(self, name: str, role: str):
        self.name = name
        self.role = role
        self.permissions: List[str] = []

    def to_dict(self) -> dict:
        return {"name": self.name, "role": self.role, "permissions": self.permissions}


class TeamManager:
    """Manage team members, projects, and role-based access."""

    DEFAULT_ROLES = ["owner", "admin", "developer", "viewer"]

    def __init__(self):
        self.members: Dict[str, TeamMember] = {}
        self.projects: Dict[str, Dict] = {}

    def add_member(self, name: str, role: str = "developer") -> dict:
        if role not in self.DEFAULT_ROLES:
            raise ValueError(f"role must be one of {self.DEFAULT_ROLES}")
        self.members[name] = TeamMember(name, role)
        return self.members[name].to_dict()

    def remove_member(self, name: str):
        return self.members.pop(name, None) is not None

    def list_members(self) -> List[dict]:
        return [m.to_dict() for m in self.members.values()]

    def create_project(self, name: str, owner: str) -> dict:
        project = {
            "name": name,
            "owner": owner,
            "members": [owner],
            "created": "now",
        }
        self.projects[name] = project
        return project

    def can(self, member: str, action: str) -> bool:
        if member not in self.members:
            return False
        role = self.members[member].role
        if role == "owner":
            return True
        if action == "view":
            return True
        if action == "edit":
            return role in ("admin", "developer")
        if action == "deploy":
            return role in ("admin",)
        return False
