"""
Signal handlers for automatic model creation and updates
"""
from django.db.models.signals import post_save, post_delete, pre_delete
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Sum
from .models import UserProfile, UserPreference, File, ActivityFeed
import logging

logger = logging.getLogger(__name__)


def recalculate_storage(user):
    """Recalculate and save storage_quota_usage_bytes for a user."""
    total = File.objects.filter(
        owner=user,
        trashed=False,
        size_bytes__isnull=False
    ).exclude(
        mime_type='folder'
    ).aggregate(total=Sum('size_bytes'))['total'] or 0

    UserProfile.objects.filter(user=user).update(storage_quota_usage_bytes=total)


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create UserProfile and UserPreference when User is created"""
    if created:
        try:
            # Create user profile
            UserProfile.objects.create(
                user=instance,
                given_name=instance.first_name,
                family_name=instance.last_name,
            )
            
            # Create user preferences
            UserPreference.objects.create(user=instance)
            
            # Create root folder
            root_folder = File.objects.create(
                name='My Drive',
                owner=instance,
                parent=None,
                mime_type='folder',
                description='Your personal file storage'
            )
            
            logger.info(f"User profile and preferences created for user: {instance.email}")
        except Exception as e:
            logger.error(f"Error creating user profile for {instance.email}: {str(e)}")


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Save UserProfile when User is saved"""
    try:
        instance.profile.save()
    except UserProfile.DoesNotExist:
        pass


@receiver(pre_delete, sender=File)
def trash_file_before_delete(sender, instance, **kwargs):
    """Move file to trash before deletion"""
    if not instance.trashed:
        # Use update() to avoid triggering post_save signal which causes FK conflicts
        File.objects.filter(pk=instance.pk).update(
            trashed=True,
            trashed_time=timezone.now()
        )
        logger.info(f"File moved to trash: {instance.name} (ID: {instance.id})")


@receiver(post_save, sender=File)
def update_storage_on_file_save(sender, instance, **kwargs):
    """Recalculate owner storage when a file is saved (upload, trash, restore)."""
    try:
        recalculate_storage(instance.owner)
    except Exception as e:
        logger.error(f"Error updating storage for {instance.owner}: {str(e)}")


@receiver(post_delete, sender=File)
def update_storage_on_file_delete(sender, instance, **kwargs):
    """Recalculate owner storage when a file is permanently deleted."""
    try:
        # Owner may already be deleted (user deletion cascade), skip safely
        if User.objects.filter(pk=instance.owner_id).exists():
            recalculate_storage(instance.owner)
    except Exception as e:
        logger.error(f"Error updating storage for {instance.owner_id}: {str(e)}")
