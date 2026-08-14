"""
core/exceptions.py
==================
Exceptions custom pour l'application.
Permet une gestion d'erreur granulaire et informative.
"""


class MeteoVeloException(Exception):
    """Exception de base pour l'application."""
    pass


class GPXError(MeteoVeloException):
    """Erreur lors de la lecture/parsing du fichier GPX."""
    pass


class WeatherError(MeteoVeloException):
    """Erreur lors de la récupération des données météo."""
    pass


class WeatherRateLimitError(WeatherError):
    """Erreur 429 : limite de requêtes atteinte."""
    pass


class OSMError(MeteoVeloException):
    """Erreur lors de la récupération de données OpenStreetMap."""
    pass


class GeminiError(MeteoVeloException):
    """Erreur lors de l'appel à l'API Gemini (Coach IA)."""
    pass


class ValidationError(MeteoVeloException):
    """Erreur de validation des données d'entrée."""
    
    def __init__(self, field_name: str, message: str):
        """
        Args:
            field_name: Nom du champ invalide
            message: Description du problème
        """
        self.field_name = field_name
        self.message = message
        super().__init__(f"Erreur validation [{field_name}]: {message}")


class ConfigError(MeteoVeloException):
    """Erreur de configuration."""
    pass


class DataProcessingError(MeteoVeloException):
    """Erreur générale lors du traitement des données."""
    
    def __init__(self, stage: str, original_error: Exception = None):
        """
        Args:
            stage: Étape où l'erreur s'est produite (ex. "calcul_parcours")
            original_error: Exception originale si disponible
        """
        self.stage = stage
        self.original_error = original_error
        message = f"Erreur lors de [{stage}]"
        if original_error:
            message += f": {str(original_error)}"
        super().__init__(message)
