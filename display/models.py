from django.db import models

class GabaritPage(models.Model):
    nom = models.CharField(max_length=100, verbose_name="Nom du gabarit")
    nombre_colonnes = models.PositiveIntegerField(default=1, verbose_name="Nombre de colonnes")
    
    class Meta:
        verbose_name = "Gabarit de page"
        verbose_name_plural = "Gabarits de page"

    def __str__(self):
        return self.nom

class TemplateIDML(models.Model):
    gabarit = models.OneToOneField(GabaritPage, on_delete=models.CASCADE, related_name='template_idml')
    fichier = models.FileField(upload_to='idml_templates/', verbose_name="Fichier IDML")
    
    class Meta:
        verbose_name = "Template IDML"
        verbose_name_plural = "Templates IDML"

    def __str__(self):
        return f"IDML pour {self.gabarit.nom}"

class TemplateLaTeX(models.Model):
    gabarit = models.OneToOneField(GabaritPage, on_delete=models.CASCADE, related_name='template_latex')
    fichier = models.FileField(upload_to='latex_templates/', verbose_name="Fichier LaTeX")
    
    class Meta:
        verbose_name = "Template LaTeX"
        verbose_name_plural = "Templates LaTeX"

    def __str__(self):
        return f"LaTeX pour {self.gabarit.nom}"