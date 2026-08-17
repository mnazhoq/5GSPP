"""
Experimental Results Script
Generate comprehensive evaluation metrics and visualizations for the Event-State Model-based DBN approach (Approach 2).
"""

import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from event_lstm_model import EventLSTMModel
from train_lstm import train_model
import warnings
warnings.filterwarnings('ignore')


class ExperimentRunner:
    """Run experiments and generate results"""
    
    def __init__(self, output_dir='./results'):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.results = {}
    
    def run_experiment(self, experiment_name, data_file, config_list):
        """
        Run experiment with multiple configurations
        
        Args:
            experiment_name (str): Name of experiment
            data_file (str): Path to data file
            config_list (list): List of configuration dicts
        """
        print(f"\n{'='*80}")
        print(f"EXPERIMENT: {experiment_name}")
        print(f"{'='*80}")
        
        results = []
        models = []
        
        for i, config in enumerate(config_list):
            print(f"\n--- Configuration {i+1}/{len(config_list)} ---")
            print(f"Config: {config}")
            
            # Train model
            model_dir = self.output_dir / f"{experiment_name}_config_{i}"
            model = train_model(data_file, str(model_dir), config)
            
            if model is None:
                continue
            
            models.append(model)
            
            # Prepare data
            data = model.load_data(data_file)
            X, y, posture_values = model.create_sequences(data)
            
            # Evaluate
            metrics = model.evaluate(X, y)
            
            # Store results
            result = {
                'config_id': i,
                'config': config,
                'accuracy': metrics['overall_accuracy'],
                'per_step_accuracy': metrics['per_step_accuracy'],
                'loss': metrics['test_loss'],
                'sample_size': len(X)
            }
            results.append(result)
            
            print(f"  Accuracy: {metrics['overall_accuracy']:.4f}")
            print(f"  Loss: {metrics['test_loss']:.4f}")
        
        self.results[experiment_name] = {
            'results': results,
            'models': models,
            'data_file': data_file
        }
        
        return results, models
    
    def experiment_1_window_size(self, data_file):
        """
        Experiment 1: Effect of different window sizes
        Similar to Fig. 26(a)
        """
        window_sizes = [2, 3, 5, 10]
        config_list = [
            {
                'window_size': ws,
                'prediction_steps': 1,
                'lstm_units': 64,
                'epochs': 30,
                'batch_size': 32
            }
            for ws in window_sizes
        ]
        
        results, models = self.run_experiment(
            'e1_window_size',
            data_file,
            config_list
        )
        
        return results
    
    def experiment_2_prediction_steps(self, data_file):
        """
        Experiment 2: Effect of different prediction steps (observed conditions)
        Similar to Fig. 26(b)
        """
        prediction_steps = [1, 2, 3, 4]
        config_list = [
            {
                'window_size': 3,
                'prediction_steps': ps,
                'lstm_units': 64,
                'epochs': 30,
                'batch_size': 32
            }
            for ps in prediction_steps
        ]
        
        results, models = self.run_experiment(
            'e2_prediction_steps',
            data_file,
            config_list
        )
        
        return results
    
    def experiment_3_combined_conditions(self, data_file):
        """
        Experiment 3: Combination of window size and prediction steps
        Similar to Fig. 26(c)
        """
        config_list = [
            {'window_size': 2, 'prediction_steps': 2, 'lstm_units': 64, 'epochs': 30, 'batch_size': 32},
            {'window_size': 3, 'prediction_steps': 2, 'lstm_units': 64, 'epochs': 30, 'batch_size': 32},
            {'window_size': 2, 'prediction_steps': 3, 'lstm_units': 64, 'epochs': 30, 'batch_size': 32},
            {'window_size': 3, 'prediction_steps': 3, 'lstm_units': 64, 'epochs': 30, 'batch_size': 32},
        ]
        
        results, models = self.run_experiment(
            'e3_combined_conditions',
            data_file,
            config_list
        )
        
        return results
    
    def experiment_4_lstm_units(self, data_file):
        """
        Experiment 4: Effect of different LSTM units
        """
        lstm_units = [32, 64, 128, 256]
        config_list = [
            {
                'window_size': 3,
                'prediction_steps': 1,
                'lstm_units': units,
                'epochs': 30,
                'batch_size': 32
            }
            for units in lstm_units
        ]
        
        results, models = self.run_experiment(
            'e4_lstm_units',
            data_file,
            config_list
        )
        
        return results
    
    def experiment_5_dropout(self, data_file):
        """
        Experiment 5: Effect of different dropout rates
        """
        dropout_rates = [0.0, 0.2, 0.5, 0.7]
        config_list = [
            {
                'window_size': 3,
                'prediction_steps': 1,
                'lstm_units': 64,
                'dropout_rate': dr,
                'epochs': 30,
                'batch_size': 32
            }
            for dr in dropout_rates
        ]
        
        results, models = self.run_experiment(
            'e5_dropout',
            data_file,
            config_list
        )
        
        return results
    
    def plot_results(self):
        """Generate visualization plots similar to Fig. 26"""
        
        if not self.results:
            print("No results to plot")
            return
        
        # Plot for each experiment
        for exp_name, exp_data in self.results.items():
            results = exp_data['results']
            
            if not results:
                continue
            
            print(f"\nPlotting results for {exp_name}...")
            
            fig, axes = plt.subplots(2, 2, figsize=(14, 10))
            fig.suptitle(f'Experimental Results: {exp_name}', fontsize=16, fontweight='bold')
            
            # Extract data
            configs = [r['config'] for r in results]
            accuracies = [r['accuracy'] for r in results]
            losses = [r['loss'] for r in results]
            sample_sizes = [r['sample_size'] for r in results]
            
            # Determine x-axis labels
            if exp_name == 'e1_window_size':
                x_labels = [f"Window {c['window_size']}" for c in configs]
                x_pos = [c['window_size'] for c in configs]
            elif exp_name == 'e2_prediction_steps':
                x_labels = [f"Steps {c['prediction_steps']}" for c in configs]
                x_pos = [c['prediction_steps'] for c in configs]
            elif exp_name == 'e3_combined_conditions':
                x_labels = [f"W{c['window_size']}S{c['prediction_steps']}" for c in configs]
                x_pos = list(range(len(configs)))
            elif exp_name == 'e4_lstm_units':
                x_labels = [f"{c['lstm_units']}" for c in configs]
                x_pos = [c['lstm_units'] for c in configs]
            elif exp_name == 'e5_dropout':
                x_labels = [f"{c['dropout_rate']}" for c in configs]
                x_pos = [c['dropout_rate'] for c in configs]
            else:
                x_labels = [f"Config {i}" for i in range(len(configs))]
                x_pos = list(range(len(configs)))
            
            # Plot 1: Accuracy
            axes[0, 0].bar(x_pos, accuracies, color='steelblue', alpha=0.7)
            axes[0, 0].set_xlabel('Configuration')
            axes[0, 0].set_ylabel('Accuracy')
            axes[0, 0].set_title('Model Accuracy')
            axes[0, 0].set_xticks(x_pos)
            axes[0, 0].set_xticklabels(x_labels, rotation=45)
            axes[0, 0].grid(True, alpha=0.3)
            
            # Plot 2: Loss
            axes[0, 1].bar(x_pos, losses, color='coral', alpha=0.7)
            axes[0, 1].set_xlabel('Configuration')
            axes[0, 1].set_ylabel('Loss')
            axes[0, 1].set_title('Model Loss')
            axes[0, 1].set_xticks(x_pos)
            axes[0, 1].set_xticklabels(x_labels, rotation=45)
            axes[0, 1].grid(True, alpha=0.3)
            
            # Plot 3: Per-step accuracy (if available)
            per_step_accs = [r['per_step_accuracy'] for r in results]
            if per_step_accs and len(per_step_accs[0]) > 0:
                max_steps = max(len(psa) for psa in per_step_accs)
                for config_idx, psa in enumerate(per_step_accs):
                    axes[1, 0].plot(range(len(psa)), psa, marker='o', label=x_labels[config_idx])
                axes[1, 0].set_xlabel('Prediction Step')
                axes[1, 0].set_ylabel('Accuracy')
                axes[1, 0].set_title('Per-Step Accuracy')
                axes[1, 0].legend()
                axes[1, 0].grid(True, alpha=0.3)
            
            # Plot 4: Summary table
            axes[1, 1].axis('off')
            summary_text = "Experiment Summary\n" + "="*30 + "\n"
            for i, result in enumerate(results):
                summary_text += f"\n{x_labels[i]}:\n"
                summary_text += f"  Accuracy: {result['accuracy']:.4f}\n"
                summary_text += f"  Loss: {result['loss']:.4f}\n"
                summary_text += f"  Samples: {result['sample_size']}\n"
            
            axes[1, 1].text(0.1, 0.9, summary_text, transform=axes[1, 1].transAxes,
                           fontsize=10, verticalalignment='top', family='monospace')
            
            plt.tight_layout()
            
            # Save figure
            fig_path = self.output_dir / f'{exp_name}_results.png'
            plt.savefig(fig_path, dpi=300, bbox_inches='tight')
            print(f"  Saved to {fig_path}")
            plt.close()
    
    def generate_report(self):
        """Generate detailed experiment report"""
        
        report_path = self.output_dir / 'EXPERIMENT_REPORT.md'
        
        with open(report_path, 'w') as f:
            f.write("# Experimental Results Report\n\n")
            f.write(f"Generated from experiments in: {self.output_dir}\n\n")
            
            for exp_name, exp_data in self.results.items():
                results = exp_data['results']
                
                f.write(f"## Experiment: {exp_name}\n\n")
                f.write(f"Data File: {exp_data['data_file']}\n\n")
                
                # Create results table
                f.write("| Config | Accuracy | Loss | Samples |\n")
                f.write("|--------|----------|------|----------|\n")
                
                for result in results:
                    f.write(f"| Config {result['config_id']} | {result['accuracy']:.4f} | ")
                    f.write(f"{result['loss']:.4f} | {result['sample_size']} |\n")
                
                f.write("\n### Configuration Details\n\n")
                for result in results:
                    f.write(f"**Config {result['config_id']}:**\n")
                    f.write("```json\n")
                    f.write(json.dumps(result['config'], indent=2))
                    f.write("\n```\n\n")
            
            f.write("\n---\n")
            f.write("Report generated by ExperimentRunner\n")
        
        print(f"\nReport saved to {report_path}")


def main():
    parser = argparse.ArgumentParser(
        description='Run experiments and generate results for Event LSTM Model'
    )
    
    parser.add_argument(
        '--data-file', '-d',
        required=True,
        help='Path to data file (CSV or TXT)'
    )
    
    parser.add_argument(
        '--output-dir', '-o',
        default='./results',
        help='Directory to save results (default: ./results)'
    )
    
    parser.add_argument(
        '--experiments', '-e',
        nargs='+',
        default=['all'],
        choices=['all', 'e1', 'e2', 'e3', 'e4', 'e5'],
        help='Experiments to run (default: all)'
    )
    
    parser.add_argument(
        '--no-plot',
        action='store_true',
        help='Skip plotting results'
    )
    
    args = parser.parse_args()
    
    # Create experiment runner
    runner = ExperimentRunner(args.output_dir)
    
    # Run experiments
    experiments_to_run = args.experiments
    if 'all' in experiments_to_run:
        experiments_to_run = ['e1', 'e2', 'e3', 'e4', 'e5']
    
    if 'e1' in experiments_to_run:
        runner.experiment_1_window_size(args.data_file)
    
    if 'e2' in experiments_to_run:
        runner.experiment_2_prediction_steps(args.data_file)
    
    if 'e3' in experiments_to_run:
        runner.experiment_3_combined_conditions(args.data_file)
    
    if 'e4' in experiments_to_run:
        runner.experiment_4_lstm_units(args.data_file)
    
    if 'e5' in experiments_to_run:
        runner.experiment_5_dropout(args.data_file)
    
    # Generate plots
    if not args.no_plot:
        runner.plot_results()
    
    # Generate report
    runner.generate_report()
    
    print("\n" + "="*80)
    print("ALL EXPERIMENTS COMPLETED")
    print("="*80)


if __name__ == '__main__':
    main()
