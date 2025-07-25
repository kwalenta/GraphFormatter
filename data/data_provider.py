import pandas as pd
import numpy as np

class DataProvider:
    """
    Provides the data used in the plotting tool.
    Can be extended to support different data sources.
    """

    def __init__(self, seed: int = 0):
        self.seed = seed
        np.random.seed(self.seed)

    def __generate_dummy_data(self, rows: int = 50, columns: int = 10) -> pd.DataFrame:
        """
        Generates dummy time series data.

        Args:
            rows (int): Number of rows (timestamps).
            columns (int): Number of data series.

        Returns:
            pd.DataFrame: DataFrame with shape (rows, columns)
        """
        column_names = [f"Series {chr(65+i)}" for i in range(columns)]
        data = np.random.randint(0, 100, size=(rows, columns))
        return pd.DataFrame(data, columns=column_names)
    
    def load_data(self, file_path: str) -> pd.DataFrame:
        """
        Loads data from a CSV file.

        Args:
            file_path (str): Path to the CSV file.

        Returns:
            pd.DataFrame: DataFrame containing the loaded data.
        """
        try:
            return pd.read_csv(file_path)
        except Exception as e:
            print(f"Error loading data from {file_path}: {e}")
            data = self.__generate_dummy_data()
            print(f"Generated dummy data with shape: {data.shape} and columns: {data.columns.tolist()}")
            return pd.DataFrame()
