import yaml
import sys
import os
from typing import Dict, Any, List
import logging
import io
import subprocess
import tempfile
import shutil
import requests
import toml

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


class ConfigurationError(Exception):
    """Custom exception for configuration-related errors"""
    pass


class CargoDependencyAnalyzer:
    """Main class for handling Cargo package dependency analysis"""
    
    VALID_MODES = ['analyze', 'test', 'visualize', 'report']
    
    def __init__(self, config_file: str = "config.yaml"):
        self.config_file = config_file
        self.config: Dict[str, Any] = {}
        self.temp_dir = None
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
    
    def clone_repository(self) -> str:
        """Clone the repository to a temporary directory"""
        try:
            self.temp_dir = tempfile.mkdtemp()
            logger.info(f"Клонируем репозиторий в: {self.temp_dir}")
            
            result = subprocess.run([
                'git', 'clone', 
                self.config['repository_url'], 
                self.temp_dir
            ], capture_output=True, text=True, check=True)
            
            logger.info("Репозиторий успешно клонирован")
            return self.temp_dir
            
        except subprocess.CalledProcessError as e:
            raise ConfigurationError(f"Ошибка клонирования репозитория: {e.stderr}")
    
    def find_cargo_toml(self, directory: str) -> str:
        """Find Cargo.toml in the repository"""
        cargo_toml_path = os.path.join(directory, 'Cargo.toml')
        
        if os.path.exists(cargo_toml_path):
            return cargo_toml_path
        
        for root, dirs, files in os.walk(directory):
            if 'Cargo.toml' in files:
                return os.path.join(root, 'Cargo.toml')
        
        raise ConfigurationError("Cargo.toml не найден в репозитории")
    
    def extract_dependencies(self, cargo_toml_path: str) -> Dict[str, Any]:
        """Extract dependencies from Cargo.toml"""
        try:
            with open(cargo_toml_path, 'r', encoding='utf-8') as file:
                cargo_data = toml.load(file)
            
            dependencies = {}
            
            if 'dependencies' in cargo_data:
                dependencies.update(cargo_data['dependencies'])

            if 'dev-dependencies' in cargo_data:
                dependencies.update(cargo_data['dev-dependencies'])
            

            if 'build-dependencies' in cargo_data:
                dependencies.update(cargo_data['build-dependencies'])
            
            return dependencies
            
        except Exception as e:
            raise ConfigurationError(f"Ошибка парсинга Cargo.toml: {e}")
    
    def format_dependency(self, name: str, dep_spec: Any) -> str:
        """Format dependency information based on its type"""
        if isinstance(dep_spec, str):
            return f"{name} = \"{dep_spec}\""
        elif isinstance(dep_spec, dict):
            if 'git' in dep_spec:
                return f"{name} = {{ git = \"{dep_spec['git']}\" }}"
            elif 'path' in dep_spec:
                return f"{name} = {{ path = \"{dep_spec['path']}\" }}"
            elif 'version' in dep_spec:
                return f"{name} = \"{dep_spec['version']}\""
            else:
                return f"{name} = {dep_spec}"
        else:
            return f"{name} = {dep_spec}"
    
    def display_configuration(self) -> None:
        """Display all user-configurable parameters in key-value format"""
        print("=== Юзером конфигурированый параметр ===")
        for key, value in self.config.items():
            print(f"{key}: {value}")
        print("====================================")
    
    def analyze_dependencies(self) -> None:
        """Main analysis method for Rust/Cargo dependencies"""
        logger.info(f"Начнем же анализ: {self.config['package_name']}")
        logger.info(f"Репризеторий: {self.config['repository_url']}")
        logger.info(f"Режим: {self.config['working_mode']}")
        
        try:

            repo_dir = self.clone_repository()
            

            cargo_toml_path = self.find_cargo_toml(repo_dir)
            logger.info(f"Найден Cargo.toml: {cargo_toml_path}")
            

            dependencies = self.extract_dependencies(cargo_toml_path)
            

            self.display_dependency_analysis(dependencies)
            
        finally:

            if self.temp_dir and os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
    
    def display_dependency_analysis(self, dependencies: Dict[str, Any]) -> None:
        """Display the dependency analysis results"""
        print("\n=== ПРЯМЫЕ ЗАВИСИМОСТИ ===")
        
        filtered_deps = {
            name: spec for name, spec in dependencies.items() 
            if self.config['filter_substring'] in name or not self.config['filter_substring']
        }
        
        if not filtered_deps:
            print("Нет зависимостей, соответствующих фильтру")
        else:
            for name, spec in filtered_deps.items():
                formatted_dep = self.format_dependency(name, spec)
                print(formatted_dep)
        
        print(f"\nВсего зависимостей: {len(dependencies)}")
        print(f"Отфильтровано: {len(filtered_deps)}")
        print("===================================")


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    """Main entry point of the application"""
    try:
        analyzer = CargoDependencyAnalyzer("config.yaml")
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
