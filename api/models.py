# models.py
from django.db import models

class ScriptRunner(models.Model):
    name = models.CharField(max_length=200, default="Script")
    script_code = models.TextField(help_text="Write your Python script here")
    output = models.TextField(blank=True, null=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    executed_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        verbose_name = "Script Runner"
        verbose_name_plural = "Script Runners"
    
    def __str__(self):
        return f"{self.name} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"

