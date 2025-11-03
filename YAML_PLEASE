import yaml
import sys
import os
from typing import Dict, Any
import logging
import io

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


class ConfigurationError(Exception):
    """Custom exception for configuration-related errors"""
    pass


class DependencyAnalyzer:
    """Main class for handling configuration and analysis"""
    
    VALID_MODES = ['analyze', 'test', 'visualize', 'report']
    
    def __init__(self, config_file: str = "config.yaml"):
        self.config_file = config_file
        self.config: Dict[str, Any] = {}
        self.load_configuration()
    
    def load_configuration(self) -> None:
        """Load and validate configuration from YAML file"""
        try:

            if not os.path.exists(self.config_file):
                raise ConfigurationError(f"Конфиг файл '{self.config_file}' не найден")
            
            if not os.access(self.config_file, os.R_OK):
                raise ConfigurationError(f"Конфиг '{self.config_file}' не читаем")
            
            with open(self.config_file, 'r', encoding='utf-8') as file:
                self.config = yaml.safe_load(file)
            
            if self.config is None:
                raise ConfigurationError("Тут пусто милорд")
            
            self._validate_configuration()
            
        except yaml.YAMLError as e:
            raise ConfigurationError(f"Неверный формат йамала: {e}")
        except IOError as e:
            raise ConfigurationError(f"Ошибка чтения конфига: {e}")
        except Exception as e:
            raise ConfigurationError(f"Внезапная ошибка грузки конфига: {e}")
    
    def _validate_configuration(self) -> None:
        """Validate all configuration parameters"""
        
        required_params = [
            'package_name', 
            'repository_url', 
            'working_mode', 
            'max_depth', 
            'filter_substring'
        ]
        
        missing_params = [param for param in required_params if param not in self.config]
        if missing_params:
            raise ConfigurationError(f"Missing required parameters: {', '.join(missing_params)}")
        
        package_name = self.config['package_name']
        if not isinstance(package_name, str):
            raise ConfigurationError("package_name must be a string")
        if not package_name.strip():
            raise ConfigurationError("package_name cannot be empty")
        
        repository_url = self.config['repository_url']
        if not isinstance(repository_url, str):
            raise ConfigurationError("repository_url must be a string")
        if not repository_url.strip():
            raise ConfigurationError("repository_url cannot be empty")
        
        working_mode = self.config['working_mode']
        if not isinstance(working_mode, str):
            raise ConfigurationError("working_mode must be a string")
        if working_mode not in self.VALID_MODES:
            valid_modes_str = ', '.join(self.VALID_MODES)
            raise ConfigurationError(f"working_mode must be one of: {valid_modes_str}")
        
        max_depth = self.config['max_depth']
        if not isinstance(max_depth, int):
            raise ConfigurationError("max_depth must be an integer")
        if max_depth < 1 or max_depth > 10:
            raise ConfigurationError("max_depth must be between 1 and 10")
        
        filter_substring = self.config['filter_substring']
        if not isinstance(filter_substring, str):
            raise ConfigurationError("filter_substring must be a string")
    
    def display_configuration(self) -> None:
        """Display all user-configurable parameters in key-value format"""
        print("=== Юзером конфигурированый параметр ===")
        for key, value in self.config.items():
            print(f"{key}: {value}")
        print("====================================")
    
    def analyze_dependencies(self) -> None:
        """
        Main analysis method (stub for this stage)
        In future stages, this would perform the actual dependency analysis
        """
        logger.info(f"Начнем же анализ: {self.config['package_name']}")
        logger.info(f"Репризеторий: {self.config['repository_url']}")
        logger.info(f"Режим: {self.config['working_mode']}")
        logger.info(f"Макс глубина: {self.config['max_depth']}")
        logger.info(f"Фильтер: {self.config['filter_substring']}")
        
        print("\n=== Итоги веселья ===")
        print("Отличная конфигурация")
        print("Параметры на высоте")
        print("Все выполнено хорошо")
        print("===================================")


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    """Main entry point of the application"""
    try:

        analyzer = DependencyAnalyzer("config.yaml")
        

        analyzer.display_configuration()
        

        analyzer.analyze_dependencies()
        
        logger.info("Сделано...")
        return 0
        
    except ConfigurationError as e:
        logger.error(f"Ерр конфига: {e}")
        return 1
    except KeyboardInterrupt:
        logger.info("Отменено пользователем")
        return 1
    except Exception as e:
        logger.error(f"Внезапный бардак ерр: {e}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
