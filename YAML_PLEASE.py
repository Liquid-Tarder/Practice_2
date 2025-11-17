import sys
import os
import re
import subprocess
import json
from datetime import datetime
from typing import Dict, Any, List, Set, Optional, Tuple
from collections import deque, defaultdict
import logging
import importlib.util

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


class ConfigurationError(Exception):
    """Custom exception for configuration-related errors"""
    pass


class GitManager:
    """Handles Git operations for saving results"""
    
    @staticmethod
    def commit_results(commit_message: str, files_to_add: List[str] = None) -> bool:
        """Commit analysis results to the repository"""
        try:

            if files_to_add:
                for file in files_to_add:
                    subprocess.run(['git', 'add', file], check=True, capture_output=True)
            else:
                subprocess.run(['git', 'add', '.'], check=True, capture_output=True)

            result = subprocess.run(
                ['git', 'commit', '-m', commit_message],
                check=True,
                capture_output=True,
                text=True
            )
            logger.info(f"Successfully committed results: {commit_message}")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Git commit failed: {e}")
            if e.stderr:
                logger.error(f"Git error: {e.stderr}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during Git commit: {e}")
            return False
    
    @staticmethod
    def get_current_branch() -> str:
        """Get current Git branch name"""
        try:
            result = subprocess.run(
                ['git', 'branch', '--show-current'],
                check=True,
                capture_output=True,
                text=True
            )
            return result.stdout.strip()
        except Exception as e:
            logger.warning(f"Could not determine current branch: {e}")
            return "unknown"


class DependencyAnalyzer:
    """Main class for handling configuration and analysis"""
    
    VALID_MODES = ['analyze', 'test', 'visualize', 'report', 'display_loading_order']
    
    def __init__(self, config_file: str = "config.py"):
        self.config_file = config_file
        self.config: Dict[str, Any] = {}
        self.dependency_graph: Dict[str, List[str]] = {}
        self.visited: Set[str] = set()
        self.loading_order: List[str] = []
        self.load_configuration()
    
    def load_configuration(self) -> None:
        """Load and validate configuration from Python file"""
        try:
            if not os.path.exists(self.config_file):
                raise ConfigurationError(f"Configuration file '{self.config_file}' not found")
            
            if not os.access(self.config_file, os.R_OK):
                raise ConfigurationError(f"Configuration file '{self.config_file}' is not readable")
            self.config = self._load_python_config()
            
            if self.config is None:
                raise ConfigurationError("Configuration file is empty or invalid")
            
            self._validate_configuration()
            
        except Exception as e:
            raise ConfigurationError(f"Error loading configuration from Python file: {e}")
    
    def _load_python_config(self) -> Dict[str, Any]:
        """Load configuration from a Python file"""
        try:
            spec = importlib.util.spec_from_file_location("config_module", self.config_file)
            if spec is None:
                raise ConfigurationError(f"Could not load specification from '{self.config_file}'")
            
            config_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(config_module)
            config_dict = {}
            required_params = [
                'package_name', 
                'repository_url', 
                'working_mode', 
                'max_depth', 
                'filter_substring'
            ]
            
            for param in required_params:
                if hasattr(config_module, param):
                    config_dict[param] = getattr(config_module, param)
                else:
                    raise ConfigurationError(f"Missing required parameter '{param}' in configuration file")
            
            optional_params = {
                'output_format': 'json',
                'verbose': False,
                'save_results': True
            }
            
            for param, default_value in optional_params.items():
                if hasattr(config_module, param):
                    config_dict[param] = getattr(config_module, param)
                else:
                    config_dict[param] = default_value
            
            return config_dict
            
        except Exception as e:
            raise ConfigurationError(f"Error parsing Python configuration file: {e}")
    
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
                    
                    if ':' in line:
                        package, deps = line.split(':', 1)
                        package = package.strip()
                        
                        if not re.match(r'^[A-Z]+$', package):
                            logger.warning(f"Invalid package name format: {package}. Skipping.")
                            continue
                        
                        dependencies = [dep.strip() for dep in deps.split(',') if dep.strip()]
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
    
    def _simulate_package_manager_loading_order(self, start_package: str) -> List[str]:
        """
        Simulate a real package manager's dependency loading order
        This uses a topological sort approach which is common in package managers
        """
        graph = self.dependency_graph

        in_degree = defaultdict(int)
        for package in graph:
            in_degree[package] = 0
        
        for package, dependencies in graph.items():
            for dep in dependencies:
                if dep in graph:
                    in_degree[dep] += 1
        
        queue = deque([pkg for pkg in graph if in_degree[pkg] == 0])
        loading_order = []
        
        while queue:
         
            current = sorted(queue)[0]
            queue.remove(current)
            
            if current not in loading_order:
                loading_order.append(current)

            for neighbor in graph.get(current, []):
                if neighbor in in_degree:
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0:
                        queue.append(neighbor)
        if start_package not in loading_order:
            start_deps = graph.get(start_package, [])
            if start_deps:
                last_dep_index = max((loading_order.index(dep) for dep in start_deps if dep in loading_order), default=-1)
                loading_order.insert(last_dep_index + 1, start_package)
            else:
                loading_order.append(start_package)
        
        return loading_order
    
    def _get_our_loading_order(self, start_package: str) -> List[str]:
        """
        Get our tool's dependency loading order using BFS approach
        """
        visited = set()
        loading_order = []
        queue = deque([start_package])
        
        while queue:
            current = queue.popleft()
            if current not in visited and current in self.dependency_graph:
                visited.add(current)
                loading_order.append(current)
                
                for dep in self.dependency_graph.get(current, []):
                    if dep not in visited and dep in self.dependency_graph:
                        queue.append(dep)
        
        return loading_order
    
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

        if self.config['working_mode'] in ['test', 'display_loading_order']:
            self.dependency_graph = self._load_test_repository(self.config['repository_url'])
            logger.info(f"Loaded test repository with {len(self.dependency_graph)} packages")
        else:

            self.dependency_graph = self._simulate_real_repository()
        

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
        stack = deque()
        stack.append((start_package, 0, []))
        visited_in_path = set()  
        all_visited = set() 
        
        while stack:
            current_package, current_depth, current_path = stack.pop()
            
            if self._should_skip_package(current_package):
                if current_package not in results['skipped_packages']:
                    results['skipped_packages'].append(current_package)
                continue
            if current_depth > max_depth:
                continue
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

            if (not dependency_info['is_cyclic'] and 
                current_package in self.dependency_graph and 
                current_depth < max_depth):

                visited_in_path.add(current_package)

                dependencies = self.dependency_graph[current_package]
                for dep in reversed(dependencies):
                    if dep in self.dependency_graph: 
                        new_path = current_path + [current_package]
                        stack.append((dep, current_depth + 1, new_path))
 
                visited_in_path.discard(current_package)
        
        results['visited_count'] = len(all_visited)
        return results
    
    def analyze_loading_order(self) -> Dict[str, Any]:
        """
        Analyze and compare dependency loading orders
        Returns: Dict containing loading order analysis results
        """
        start_package = self.config['package_name']
        
        logger.info(f"Analyzing loading order for package: {start_package}")
        
        self.dependency_graph = self._load_test_repository(self.config['repository_url'])
        logger.info(f"Loaded test repository with {len(self.dependency_graph)} packages")

        if start_package not in self.dependency_graph:
            raise ConfigurationError(f"Package '{start_package}' not found in repository")

        our_loading_order = self._get_our_loading_order(start_package)
        simulated_pm_loading_order = self._simulate_package_manager_loading_order(start_package)

        discrepancies = []
        

        for i, (our_pkg, pm_pkg) in enumerate(zip(our_loading_order, simulated_pm_loading_order)):
            if our_pkg != pm_pkg:
                discrepancies.append({
                    'type': 'order_mismatch',
                    'position': i,
                    'our_package': our_pkg,
                    'pm_package': pm_pkg,
                    'description': f'Position {i}: We have {our_pkg}, Package Manager has {pm_pkg}'
                })

        our_set = set(our_loading_order)
        pm_set = set(simulated_pm_loading_order)
        
        missing_in_pm = our_set - pm_set
        missing_in_our = pm_set - our_set
        
        for pkg in missing_in_pm:
            discrepancies.append({
                'type': 'missing_in_pm',
                'package': pkg,
                'description': f'Package {pkg} found in our analysis but missing in package manager simulation'
            })
        
        for pkg in missing_in_our:
            discrepancies.append({
                'type': 'missing_in_our',
                'package': pkg,
                'description': f'Package {pkg} found in package manager simulation but missing in our analysis'
            })
        
        results = {
            'start_package': start_package,
            'our_loading_order': our_loading_order,
            'pm_loading_order': simulated_pm_loading_order,
            'discrepancies': discrepancies,
            'discrepancy_count': len(discrepancies),
            'analysis_timestamp': datetime.now().isoformat()
        }
        
        return results
    
    def _simulate_real_repository(self) -> Dict[str, List[str]]:
        """
        Simulate a real repository for demonstration purposes
        In a real implementation, this would fetch from actual package repository
        """
        return {
            'A': ['B', 'C'],
            'B': ['D', 'E'],
            'C': ['F', 'B'],
            'D': ['G'],
            'E': ['H', 'A'],
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
    
    def display_loading_order_results(self, results: Dict[str, Any]) -> None:
        """Display the loading order analysis results"""
        print(f"\n=== Dependency Loading Order Analysis ===")
        print(f"Start Package: {results['start_package']}")
        print(f"Analysis Timestamp: {results['analysis_timestamp']}")
        
        print(f"\n--- Ousfr Loading Order ---")
        for i, package in enumerate(results['our_loading_order']):
            print(f"  {i+1:2d}. {package}")
        
        print(f"\n--- Simulated Package Manager Loading Order ---")
        for i, package in enumerate(results['pm_loading_order']):
            print(f"  {i+1:2d}. {package}")
        
        print(f"\n--- Discrepancies Found: {results['discrepancy_count']} ---")
        if results['discrepancies']:
            for discrepancy in results['discrepancies']:
                print(f"  - {discrepancy['description']}")
            
            print(f"\n--- Discrepancy Explanations ---")
            print(f"  1. Order mismatches occur due to different traversal algorithms")
            print(f"  2. BFS vs topological sort approaches")
            print(f"  3. Different handling of dependency resolution")
            print(f"  4. Package manager may optimize for installation efficiency")
        else:
            print(f"  No discrepancies found - loading orders match!")
        
        print("===============================================")
    
    def save_results_to_file(self, results: Dict[str, Any], filename: str) -> None:
        """Save analysis results to a JSON file"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            logger.info(f"Results saved to {filename}")
        except Exception as e:
            logger.error(f"Failed to save results to {filename}: {e}")
    
    def demonstrate_test_cases(self) -> None:
        """Demonstrate various test cases with the test repository"""
        test_cases = [
            {
                'name': 'Basic dependency chain',
                'package': 'A',
                'description': 'Simple linear dependency chain'
            },
            {
                'name': 'Complex dependencies',
                'package': 'C', 
                'description': 'Package with multiple dependency levels'
            },
            {
                'name': 'Self-contained package',
                'package': 'M',
                'description': 'Package with no dependencies'
            },
            {
                'name': 'Circular dependencies',
                'package': 'E',
                'description': 'Package involved in circular dependency'
            }
        ]
        
        original_package = self.config['package_name']
        original_mode = self.config['working_mode']
        
        print("\n" + "="*60)
        print("DEMONSTRATING TEST CASES")
        print("="*60)
        
        for test_case in test_cases:
            print(f"\n--- Test Case: {test_case['name']} ---")
            print(f"Package: {test_case['package']}")
            print(f"Description: {test_case['description']}")
            
            self.config['package_name'] = test_case['package']
            self.config['working_mode'] = 'display_loading_order'
            
            try:
                results = self.analyze_loading_order()
                self.display_loading_order_results(results)
                
                safe_name = test_case['name'].replace(' ', '_').lower()
                self.save_results_to_file(
                    results, 
                    f"loading_order_{safe_name}_{test_case['package']}.json"
                )
                
            except Exception as e:
                print(f"  Error in test case: {e}")
        
        self.config['package_name'] = original_package
        self.config['working_mode'] = original_mode
    
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
        
        if self.config['working_mode'] == 'display_loading_order':
            results = self.analyze_loading_order()
            self.display_loading_order_results(results)
            
            # Save results
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"loading_order_{self.config['package_name']}_{timestamp}.json"
            self.save_results_to_file(results, filename)
            
            return results
        else:
            results = self.analyze_dependencies_dfs()
            self.display_analysis_results(results)
            return results


def main():
    """Main entry point of the application"""
    try:
        analyzer = DependencyAnalyzer("config.py")
        
        analyzer.display_configuration()
        
        if analyzer.config['working_mode'] == 'display_loading_order':
            results = analyzer.analyze_dependencies()
            
            analyzer.demonstrate_test_cases()
            
            final_filename = f"final_loading_order_{analyzer.config['package_name']}.json"
            analyzer.save_results_to_file(results, final_filename)

            commit_message = f"feat: Add dependency loading order analysis for {analyzer.config['package_name']}"
            if GitManager.commit_results(commit_message, [final_filename]):
                logger.info("Results successfully committed to repository")
            else:
                logger.warning("Failed to commit results to repository")
                
        else:
            results = analyzer.analyze_dependencies()
        
        logger.info("Stage 2 completed successfully!")
        
        if analyzer.config['working_mode'] == 'display_loading_order':
            logger.info(f"Found {results['discrepancy_count']} discrepancies in loading orders")
            logger.info("Test case demonstrations completed")
        else:
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
    sys.exit(exit_code)
