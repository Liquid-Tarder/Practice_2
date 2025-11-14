import yaml
import sys
import os
import re
from typing import Dict, Any, List, Set, Optional
from collections import deque
import logging

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
        self.dependency_graph: Dict[str, List[str]] = {}
        self.visited: Set[str] = set()
        self.load_configuration()
    
    def load_configuration(self) -> None:
        """Load and validate configuration from YAML file"""
        try:
            if not os.path.exists(self.config_file):
                raise ConfigurationError(f"Configuration file '{self.config_file}' not found")
            
            if not os.access(self.config_file, os.R_OK):
                raise ConfigurationError(f"Configuration file '{self.config_file}' is not readable")
            
            with open(self.config_file, 'r', encoding='utf-8') as file:
                self.config = yaml.safe_load(file)
            
            if self.config is None:
                raise ConfigurationError("Configuration file is empty or invalid")
            
            self._validate_configuration()
            
        except yaml.YAMLError as e:
            raise ConfigurationError(f"Invalid YAML format: {e}")
        except IOError as e:
            raise ConfigurationError(f"Error reading configuration file: {e}")
        except Exception as e:
            raise ConfigurationError(f"Unexpected error loading configuration: {e}")
    
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
    
    def _load_test_repository(self, file_path: str) -> Dict[str, List[str]]:
        """Load repository graph from file for test mode"""
        graph = {}
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                for line in file:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    # Expected format: "PACKAGE: DEP1, DEP2, DEP3"
                    if ':' in line:
                        package, deps = line.split(':', 1)
                        package = package.strip()
                        
                        # Validate package name format (uppercase letters only)
                        if not re.match(r'^[A-Z]+$', package):
                            logger.warning(f"Invalid package name format: {package}. Skipping.")
                            continue
                        
                        dependencies = [dep.strip() for dep in deps.split(',') if dep.strip()]
                        # Validate dependency names
                        valid_dependencies = []
                        for dep in dependencies:
                            if re.match(r'^[A-Z]+$', dep):
                                valid_dependencies.append(dep)
                            else:
                                logger.warning(f"Invalid dependency name format: {dep}. Skipping.")
                        
                        graph[package] = valid_dependencies
            return graph
        except FileNotFoundError:
            raise ConfigurationError(f"Test repository file '{file_path}' not found")
        except Exception as e:
            raise ConfigurationError(f"Error reading test repository file: {e}")
    
    def _should_skip_package(self, package: str) -> bool:
        """Check if package should be skipped based on filter substring"""
        return self.config['filter_substring'] in package
    
    def analyze_dependencies_dfs(self) -> Dict[str, Any]:
        """
        Analyze dependencies using iterative DFS algorithm
        Returns: Dict containing analysis results
        """
        start_package = self.config['package_name']
        max_depth = self.config['max_depth']
        filter_substring = self.config['filter_substring']
        
        logger.info(f"Starting DFS analysis for package: {start_package}")
        logger.info(f"Max depth: {max_depth}, Filter: '{filter_substring}'")
        
        # For test mode, load the repository graph from file
        if self.config['working_mode'] == 'test':
            self.dependency_graph = self._load_test_repository(self.config['repository_url'])
            logger.info(f"Loaded test repository with {len(self.dependency_graph)} packages")
        else:
            # For real analysis, this would fetch from actual repository
            # Placeholder for future implementation
            self.dependency_graph = self._simulate_real_repository()
        
        # Validate that start package exists
        if start_package not in self.dependency_graph:
            raise ConfigurationError(f"Package '{start_package}' not found in repository")
        
        results = {
            'start_package': start_package,
            'max_depth': max_depth,
            'filter_substring': filter_substring,
            'dependencies': [],
            'cyclic_dependencies': [],
            'skipped_packages': [],
            'visited_count': 0
        }
        
        # Iterative DFS implementation
        stack = deque()
        stack.append((start_package, 0, []))  # (package, current_depth, path)
        visited_in_path = set()  # Track visited packages in current path for cycle detection
        all_visited = set()  # Track all visited packages
        
        while stack:
            current_package, current_depth, current_path = stack.pop()
            
            # Skip if package contains filter substring
            if self._should_skip_package(current_package):
                if current_package not in results['skipped_packages']:
                    results['skipped_packages'].append(current_package)
                continue
            
            # Check if we've reached max depth
            if current_depth > max_depth:
                continue
            
            # Record the dependency
            dependency_info = {
                'package': current_package,
                'depth': current_depth,
                'path': current_path.copy()
            }
            
            # Check for cyclic dependency
            if current_package in visited_in_path:
                cycle_info = {
                    'package': current_package,
                    'cycle_path': current_path + [current_package]
                }
                if cycle_info not in results['cyclic_dependencies']:
                    results['cyclic_dependencies'].append(cycle_info)
                dependency_info['is_cyclic'] = True
            else:
                dependency_info['is_cyclic'] = False
            
            results['dependencies'].append(dependency_info)
            all_visited.add(current_package)
            
            # Only explore dependencies if not cyclic and within depth limit
            if (not dependency_info['is_cyclic'] and 
                current_package in self.dependency_graph and 
                current_depth < max_depth):
                
                # Add to current path for cycle detection
                visited_in_path.add(current_package)
                
                # Push dependencies to stack in reverse order to maintain DFS order
                dependencies = self.dependency_graph[current_package]
                for dep in reversed(dependencies):
                    if dep in self.dependency_graph:  # Only explore known packages
                        new_path = current_path + [current_package]
                        stack.append((dep, current_depth + 1, new_path))
                
                # Remove from current path after processing dependencies
                visited_in_path.discard(current_package)
        
        results['visited_count'] = len(all_visited)
        return results
    
    def _simulate_real_repository(self) -> Dict[str, List[str]]:
        """
        Simulate a real repository for demonstration purposes
        In a real implementation, this would fetch from actual package repository
        """
        # A sample graph with potential cycles
        return {
            'A': ['B', 'C'],
            'B': ['D', 'E'],
            'C': ['F', 'B'],
            'D': ['G'],
            'E': ['H', 'A'],  # Cycle: A -> B -> E -> A
            'F': ['I'],
            'G': ['J'],
            'H': ['K'],
            'I': ['L'],
            'J': ['M'],
            'K': ['N'],
            'L': ['O'],
            'M': [],
            'N': ['P'],
            'O': ['Q'],
            'P': ['R'],
            'Q': ['S'],
            'R': ['T'],
            'S': [],
            'T': []
        }
    
    def display_configuration(self) -> None:
        """Display all user-configurable parameters in key-value format"""
        print("=== User-Configurable Parameters ===")
        for key, value in self.config.items():
            print(f"{key}: {value}")
        print("====================================")
    
    def display_analysis_results(self, results: Dict[str, Any]) -> None:
        """Display the analysis results in a readable format"""
        print(f"\n=== Analysis Results ===")
        print(f"Start Package: {results['start_package']}")
        print(f"Max Depth: {results['max_depth']}")
        print(f"Filter Substring: '{results['filter_substring']}'")
        print(f"Total Dependencies Found: {len(results['dependencies'])}")
        print(f"Unique Packages Visited: {results['visited_count']}")
        
        print(f"\n--- Dependency Tree (DFS Order) ---")
        for dep in results['dependencies']:
            indent = "  " * dep['depth']
            cyclic_marker = " [CYCLE]" if dep['is_cyclic'] else ""
            print(f"{indent}{dep['package']}{cyclic_marker}")
        
        if results['skipped_packages']:
            print(f"\n--- Skipped Packages (containing '{results['filter_substring']}') ---")
            for package in results['skipped_packages']:
                print(f"  {package}")
        
        if results['cyclic_dependencies']:
            print(f"\n--- Cyclic Dependencies Detected ---")
            for cycle in results['cyclic_dependencies']:
                print(f"  Package: {cycle['package']}")
                print(f"  Cycle Path: {' -> '.join(cycle['cycle_path'])} -> {cycle['package']}")
        
        print("===================================")
    
    def analyze_dependencies(self) -> Dict[str, Any]:
        """
        Main analysis method that coordinates the dependency analysis
        Returns: Analysis results
        """
        logger.info(f"Starting analysis for package: {self.config['package_name']}")
        logger.info(f"Repository: {self.config['repository_url']}")
        logger.info(f"Mode: {self.config['working_mode']}")
        logger.info(f"Max depth: {self.config['max_depth']}")
        logger.info(f"Filter: {self.config['filter_substring']}")
        
        results = self.analyze_dependencies_dfs()
        self.display_analysis_results(results)
        
        return results


def main():
    """Main entry point of the application"""
    try:
        analyzer = DependencyAnalyzer("config.yaml")
        
        analyzer.display_configuration()
        
        results = analyzer.analyze_dependencies()
        
        logger.info("Stage 2 completed successfully!")
        logger.info(f"Found {len(results['dependencies'])} dependencies")
        logger.info(f"Detected {len(results['cyclic_dependencies'])} cyclic dependencies")
        
        return 0
        
    except ConfigurationError as e:
        logger.error(f"Configuration error: {e}")
        return 1
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)"
