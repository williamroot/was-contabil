"""Admin registration para models core (debug only)."""

from django.contrib import admin

from apps.core.models import Invitation, Membership, Organization


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    """Admin para Organization."""

    list_display = ("name", "slug", "created_at")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    """Admin para Membership."""

    list_display = ("user", "organization", "is_owner", "joined_at")
    list_filter = ("is_owner", "organization")
    search_fields = ("user__email", "organization__name")


@admin.register(Invitation)
class InvitationAdmin(admin.ModelAdmin):
    """Admin para Invitation."""

    list_display = ("email", "organization", "is_org_invite", "accepted_at", "expires_at", "created_at")
    list_filter = ("is_org_invite",)
    search_fields = ("email",)
    readonly_fields = ("token",)
