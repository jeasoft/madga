# Nitro 0.8 - Models y Mixins

## 2. Model Mixins

### `nitro/models.py`

```python
"""
Nitro 0.8 - Model mixins.
"""

import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone


class UUIDMixin(models.Model):
    """UUID primary key."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    class Meta:
        abstract = True


class TimestampMixin(models.Model):
    """Created/updated timestamps."""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True


class UserTrackingMixin(models.Model):
    """Track who created/updated."""
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='%(class)s_created',
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='%(class)s_updated',
    )
    
    class Meta:
        abstract = True


class SoftDeleteManager(models.Manager):
    """Excludes deleted by default."""
    
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)
    
    def with_deleted(self):
        return super().get_queryset()
    
    def only_deleted(self):
        return super().get_queryset().filter(is_deleted=True)


class SoftDeleteMixin(models.Model):
    """
    Soft delete instead of hard delete.
    
    Usage:
        class MyModel(SoftDeleteMixin, models.Model):
            name = models.CharField(max_length=100)
            
            objects = SoftDeleteManager()
            all_objects = models.Manager()
    """
    
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='%(class)s_deleted',
    )
    
    class Meta:
        abstract = True
    
    def soft_delete(self, user=None):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.deleted_by = user
        self.save(update_fields=['is_deleted', 'deleted_at', 'deleted_by'])
    
    def restore(self):
        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by = None
        self.save(update_fields=['is_deleted', 'deleted_at', 'deleted_by'])
    
    def hard_delete(self):
        super().delete()
    
    def delete(self, *args, hard=False, **kwargs):
        if hard:
            super().delete(*args, **kwargs)
        else:
            self.soft_delete()


class AuditModel(UUIDMixin, TimestampMixin, UserTrackingMixin, models.Model):
    """
    Complete audit model.
    
    Usage:
        class Property(AuditModel):
            name = models.CharField(max_length=200)
            
            class Meta(AuditModel.Meta):
                pass
    """
    
    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=['created_at']),
            models.Index(fields=['updated_at']),
        ]


class SoftDeleteAuditModel(AuditModel, SoftDeleteMixin):
    """Audit model with soft delete."""
    
    objects = SoftDeleteManager()
    all_objects = models.Manager()
    
    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=['created_at']),
            models.Index(fields=['is_deleted']),
        ]
```

---

## 3. View Mixins

### `nitro/mixins.py`

```python
"""
Nitro 0.8 - View mixins.
"""

from django.core.exceptions import PermissionDenied


class OrganizationMixin:
    """
    Base for multi-tenant views.
    """
    org_field = 'organization'
    
    def get_organization(self):
        raise NotImplementedError
    
    @property
    def organization(self):
        if not hasattr(self, '_organization'):
            self._organization = self.get_organization()
        return self._organization
    
    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(**{self.org_field: self.organization})


class CompanyMixin(OrganizationMixin):
    """
    Company-scoped views.
    
    Gets company from user's permissions.
    """
    org_field = 'company'
    
    def get_organization(self):
        user = self.request.user
        
        # Try various ways to get company
        if hasattr(user, 'company'):
            return user.company
        
        if hasattr(user, 'user_permission'):
            return user.user_permission.company
        
        if hasattr(user, 'permissions'):
            perm = user.permissions.first()
            if perm:
                return perm.company
        
        raise PermissionDenied("Usuario no tiene compañía asignada")


class StaffRequiredMixin:
    """Require staff user."""
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_staff:
            raise PermissionDenied("Acceso solo para staff")
        return super().dispatch(request, *args, **kwargs)


class SuperuserRequiredMixin:
    """Require superuser."""
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            raise PermissionDenied("Acceso solo para superusuarios")
        return super().dispatch(request, *args, **kwargs)


class PermissionRequiredMixin:
    """
    Require specific permission.
    
    class MyView(PermissionRequiredMixin, NitroView):
        permission_required = 'app.can_edit'
    """
    permission_required = None
    
    def dispatch(self, request, *args, **kwargs):
        if self.permission_required:
            if not request.user.has_perm(self.permission_required):
                raise PermissionDenied()
        return super().dispatch(request, *args, **kwargs)


class OwnerRequiredMixin:
    """
    Require user to own the object.
    
    class MyView(OwnerRequiredMixin, NitroUpdateView):
        owner_field = 'created_by'
    """
    owner_field = 'created_by'
    
    def get_object(self):
        obj = super().get_object()
        owner = getattr(obj, self.owner_field, None)
        if owner != self.request.user:
            raise PermissionDenied("No tienes permiso para editar esto")
        return obj


class CacheMixin:
    """
    Cache view response.
    
    class MyView(CacheMixin, NitroView):
        cache_timeout = 300  # 5 minutes
        cache_key_prefix = 'myview'
    """
    cache_timeout = 60
    cache_key_prefix = ''
    
    def get_cache_key(self):
        return f"{self.cache_key_prefix}:{self.request.get_full_path()}"
    
    def dispatch(self, request, *args, **kwargs):
        from django.core.cache import cache
        
        # Skip cache for authenticated users or POST
        if request.user.is_authenticated or request.method != 'GET':
            return super().dispatch(request, *args, **kwargs)
        
        cache_key = self.get_cache_key()
        response = cache.get(cache_key)
        
        if response is None:
            response = super().dispatch(request, *args, **kwargs)
            cache.set(cache_key, response, self.cache_timeout)
        
        return response
```

---

## 4. Audit Trail

### `nitro/audit.py`

```python
"""
Nitro 0.8 - Audit trail system.

Tracks changes to model instances.
"""

import json
from django.db import models
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType


class AuditLog(models.Model):
    """
    Audit log entry.
    
    Records creates, updates, and deletes.
    """
    ACTION_CHOICES = [
        ('create', 'Crear'),
        ('update', 'Actualizar'),
        ('delete', 'Eliminar'),
        ('restore', 'Restaurar'),
    ]
    
    # What was changed
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.CharField(max_length=255)
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # Who changed it
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
    )
    
    # What happened
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    changes = models.JSONField(default=dict, blank=True)
    
    # When
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # Optional context
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['action', 'timestamp']),
        ]
    
    def __str__(self):
        return f"{self.action} {self.content_type} by {self.user}"


class AuditableMixin:
    """
    Mixin to track changes to a model.
    
    Usage:
        class Property(AuditableMixin, models.Model):
            audit_fields = ['name', 'address', 'status']  # Optional: fields to track
    """
    
    audit_fields = None  # None = all fields, or list of field names
    
    def _get_tracked_fields(self):
        if self.audit_fields:
            return self.audit_fields
        return [f.name for f in self._meta.fields if f.name not in ('id', 'created_at', 'updated_at')]
    
    def _get_field_values(self):
        return {f: getattr(self, f) for f in self._get_tracked_fields()}
    
    def _serialize_value(self, value):
        """Convert value to JSON-serializable format."""
        if hasattr(value, 'pk'):
            return str(value.pk)
        if hasattr(value, 'isoformat'):
            return value.isoformat()
        return value
    
    def save_with_audit(self, user=None, request=None, **kwargs):
        """Save with audit logging."""
        is_new = self.pk is None
        
        if not is_new:
            try:
                old_instance = self.__class__.objects.get(pk=self.pk)
                old_values = old_instance._get_field_values()
            except self.__class__.DoesNotExist:
                old_values = {}
        else:
            old_values = {}
        
        # Save the instance
        super().save(**kwargs)
        
        # Prepare changes dict
        new_values = self._get_field_values()
        
        if is_new:
            changes = {k: {'new': self._serialize_value(v)} for k, v in new_values.items()}
            action = 'create'
        else:
            changes = {}
            for field in self._get_tracked_fields():
                old_val = old_values.get(field)
                new_val = new_values.get(field)
                if old_val != new_val:
                    changes[field] = {
                        'old': self._serialize_value(old_val),
                        'new': self._serialize_value(new_val),
                    }
            action = 'update'
        
        # Only log if there are changes
        if changes:
            ip_address = None
            user_agent = ''
            if request:
                ip_address = request.META.get('REMOTE_ADDR')
                user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]
            
            AuditLog.objects.create(
                content_type=ContentType.objects.get_for_model(self),
                object_id=str(self.pk),
                user=user,
                action=action,
                changes=changes,
                ip_address=ip_address,
                user_agent=user_agent,
            )
    
    def delete_with_audit(self, user=None, request=None, **kwargs):
        """Delete with audit logging."""
        ip_address = None
        user_agent = ''
        if request:
            ip_address = request.META.get('REMOTE_ADDR')
            user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]
        
        AuditLog.objects.create(
            content_type=ContentType.objects.get_for_model(self),
            object_id=str(self.pk),
            user=user,
            action='delete',
            changes={'deleted': self._get_field_values()},
            ip_address=ip_address,
            user_agent=user_agent,
        )
        
        super().delete(**kwargs)
    
    @classmethod
    def get_audit_log(cls, obj_id):
        """Get audit log for an instance."""
        ct = ContentType.objects.get_for_model(cls)
        return AuditLog.objects.filter(
            content_type=ct,
            object_id=str(obj_id),
        ).select_related('user')


def log_action(instance, action, user=None, changes=None, request=None):
    """
    Utility function to log an action.
    
    log_action(property, 'status_change', user=request.user, changes={'status': {'old': 'active', 'new': 'inactive'}})
    """
    ip_address = None
    user_agent = ''
    if request:
        ip_address = request.META.get('REMOTE_ADDR')
        user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]
    
    AuditLog.objects.create(
        content_type=ContentType.objects.get_for_model(instance),
        object_id=str(instance.pk),
        user=user,
        action=action,
        changes=changes or {},
        ip_address=ip_address,
        user_agent=user_agent,
    )
```

---

## Migration for AuditLog

```python
# Create migration: python manage.py makemigrations nitro

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='AuditLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('object_id', models.CharField(max_length=255)),
                ('action', models.CharField(choices=[('create', 'Crear'), ('update', 'Actualizar'), ('delete', 'Eliminar'), ('restore', 'Restaurar')], max_length=20)),
                ('changes', models.JSONField(blank=True, default=dict)),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('user_agent', models.CharField(blank=True, max_length=500)),
                ('content_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='contenttypes.contenttype')),
                ('user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-timestamp'],
            },
        ),
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(fields=['content_type', 'object_id'], name='nitro_audit_content_abc123_idx'),
        ),
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(fields=['user', 'timestamp'], name='nitro_audit_user_ti_def456_idx'),
        ),
    ]
```
