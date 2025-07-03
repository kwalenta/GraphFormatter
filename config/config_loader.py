import yaml

class ConfigLoader:
    """
    Loads and validates a YAML configuration for the plotting tool.
    """

    def __init__(self, config_path: str):
        self.config_path = config_path
        self.config = self._load_yaml()

    def _load_yaml(self) -> dict:
        """
        Loads the YAML file content into a dictionary.

        Returns:
            dict: The configuration dictionary.
        """
        with open(self.config_path, "r") as file:
            config = yaml.safe_load(file)

        if not isinstance(config, dict):
            raise ValueError("YAML configuration must be a dictionary at the root level.")

        return config

    def get_config(self) -> dict:
        """
        Returns the loaded configuration dictionary.
        """
        return self.config
