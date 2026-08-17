"""
Event-based LSTM Model for Security Attack Sequence Prediction
Supports configurable sliding window and multi-step prediction
"""

import numpy as np
import pandas as pd
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, mean_absolute_error
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
from tensorflow.keras.callbacks import EarlyStopping
import pickle
import json
from pathlib import Path
import ast
import warnings
warnings.filterwarnings('ignore')


class EventLSTMModel:
    """
    LSTM model for predicting future security events based on historical sequences
    """
    
    def __init__(self, config=None):
        """
        Initialize the model with configuration
        
        Args:
            config (dict): Configuration dictionary with parameters:
                - window_size: Number of previous events to use for prediction (sliding window)
                - prediction_steps: Number of future events to predict
                - lstm_units: Number of LSTM units (default: 64)
                - dropout_rate: Dropout rate (default: 0.2)
                - epochs: Number of training epochs (default: 50)
                - batch_size: Batch size (default: 32)
                - validation_split: Validation split ratio (default: 0.2)
        """
        self.config = config or {}
        self.window_size = self.config.get('window_size', 3)
        self.prediction_steps = self.config.get('prediction_steps', 1)
        self.lstm_units = self.config.get('lstm_units', 64)
        self.dropout_rate = self.config.get('dropout_rate', 0.2)
        self.epochs = self.config.get('epochs', 50)
        self.batch_size = self.config.get('batch_size', 32)
        self.validation_split = self.config.get('validation_split', 0.2)
        
        self.model = None
        self.label_encoder = LabelEncoder()
        self.all_events = None
        self.event_to_id = {}
        self.id_to_event = {}
        self.history = None
        self.scaler_posture = None
        
    def extract_events_from_sequence(self, sequence_str):
        """
        Extract events from sequence string (handles both list format and comma-separated)
        
        Args:
            sequence_str (str): Sequence string in format "['event1', 'event2', ...]" or "event1,event2,..."
            
        Returns:
            list: List of event names
        """
        try:
            # Try to parse as Python list literal
            sequence_str = sequence_str.strip()
            if sequence_str.startswith('['):
                events = ast.literal_eval(sequence_str)
                return events if isinstance(events, list) else [events]
            else:
                # Parse as comma-separated
                return [e.strip() for e in sequence_str.split(',') if e.strip()]
        except:
            return []
    
    def load_data_csv(self, file_path):
        """
        Load data from CSV file
        
        Args:
            file_path (str): Path to CSV file with columns: date_time, sequence, posturevalue
            
        Returns:
            list: List of (events, posture_value) tuples
        """
        df = pd.read_csv(file_path)
        data = []
        
        for _, row in df.iterrows():
            events = self.extract_events_from_sequence(row['sequence'])
            posture_value = float(row.get('posturevalue', 0))
            if events:  # Only add non-empty sequences
                data.append((events, posture_value))
        
        return data
    
    def load_data_txt(self, file_path):
        """
        Load data from TXT file (comma-separated events per line)
        
        Args:
            file_path (str): Path to TXT file
            
        Returns:
            list: List of (events, posture_value) tuples (posture_value will be None for txt)
        """
        data = []
        with open(file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    events = self.extract_events_from_sequence(line)
                    if events:
                        data.append((events, 0.5))  # Default posture value for txt
        
        return data
    
    def load_data(self, file_path):
        """
        Load data from either CSV or TXT file
        
        Args:
            file_path (str): Path to data file
            
        Returns:
            list: List of (events, posture_value) tuples
        """
        file_path = Path(file_path)
        
        if file_path.suffix.lower() == '.csv':
            return self.load_data_csv(str(file_path))
        elif file_path.suffix.lower() == '.txt':
            return self.load_data_txt(str(file_path))
        else:
            raise ValueError(f"Unsupported file format: {file_path.suffix}")
    
    def build_vocabulary(self, data):
        """
        Build vocabulary from all events in dataset
        
        Args:
            data (list): List of (events, posture_value) tuples
        """
        all_events = set()
        for events, _ in data:
            all_events.update(events)
        
        self.all_events = sorted(list(all_events))
        self.event_to_id = {event: idx for idx, event in enumerate(self.all_events)}
        self.id_to_event = {idx: event for event, idx in self.event_to_id.items()}
        
        print(f"Vocabulary built with {len(self.all_events)} unique events")
        print(f"Events: {self.all_events[:10]}..." if len(self.all_events) > 10 else f"Events: {self.all_events}")
    
    def create_sequences(self, data):
        """
        Create sliding window sequences for LSTM training
        
        Args:
            data (list): List of (events, posture_value) tuples
            
        Returns:
            tuple: (X, y, posture_values) where:
                - X: input sequences (window_size events encoded)
                - y: target sequences (prediction_steps events encoded)
                - posture_values: corresponding posture values
        """
        X = []
        y = []
        posture_values = []
        
        # Flatten all sequences into one sequence
        all_sequence = []
        all_postures = []
        
        for events, posture in data:
            for event in events:
                if event in self.event_to_id:
                    all_sequence.append(self.event_to_id[event])
                    all_postures.append(posture)
        
        # Create sliding windows
        min_length = self.window_size + self.prediction_steps
        
        for i in range(len(all_sequence) - min_length + 1):
            # Input: window_size events
            window = all_sequence[i:i + self.window_size]
            
            # Target: prediction_steps events
            target = all_sequence[i + self.window_size:i + self.window_size + self.prediction_steps]
            
            # Pad if necessary
            if len(target) < self.prediction_steps:
                target = target + [0] * (self.prediction_steps - len(target))
            
            X.append(window)
            y.append(target)
            # Use posture from first event in window
            posture_values.append(all_postures[i])
        
        return np.array(X), np.array(y), np.array(posture_values)
    
    def build_model(self, vocab_size):
        """
        Build LSTM model architecture
        
        Args:
            vocab_size (int): Size of vocabulary (number of unique events)
        """
        self.model = Sequential([
            keras.layers.Embedding(vocab_size + 1, 32, input_length=self.window_size),
            LSTM(self.lstm_units, return_sequences=True),
            Dropout(self.dropout_rate),
            LSTM(self.lstm_units, return_sequences=False),
            Dropout(self.dropout_rate),
            Dense(64, activation='relu'),
            Dense(self.prediction_steps * vocab_size, activation='softmax')
        ])
        
        self.model.compile(
            optimizer='adam',
            loss='sparse_categorical_crossentropy',
            metrics=['accuracy']
        )
        
        print(self.model.summary())
    
    def train(self, X, y, validation_data=None):
        """
        Train the LSTM model
        
        Args:
            X (np.array): Input sequences
            y (np.array): Target sequences
            validation_data (tuple): Validation data (X_val, y_val)
        """
        callbacks = [
            EarlyStopping(monitor='val_loss' if validation_data else 'loss', 
                         patience=5, restore_best_weights=True)
        ]
        
        self.history = self.model.fit(
            X, y,
            epochs=self.epochs,
            batch_size=self.batch_size,
            validation_split=self.validation_split if not validation_data else 0,
            validation_data=validation_data,
            callbacks=callbacks,
            verbose=1
        )
    
    def predict_events(self, event_sequence):
        """
        Predict next events given a sequence
        
        Args:
            event_sequence (list): List of event names
            
        Returns:
            list: Predicted event names
        """
        # Encode events
        encoded = [self.event_to_id.get(event, 0) for event in event_sequence[-self.window_size:]]
        
        # Pad if necessary
        if len(encoded) < self.window_size:
            encoded = [0] * (self.window_size - len(encoded)) + encoded
        
        # Predict
        input_array = np.array([encoded])
        predictions = self.model.predict(input_array, verbose=0)
        
        # Get predicted event IDs
        predictions = predictions[0].reshape(-1, len(self.all_events))
        predicted_ids = [np.argmax(predictions[i]) for i in range(self.prediction_steps)]
        
        # Decode to event names
        predicted_events = [self.id_to_event.get(idx, 'UNKNOWN') for idx in predicted_ids]
        
        return predicted_events
    
    def predict_with_confidence(self, event_sequence):
        """
        Predict next events with confidence scores
        
        Args:
            event_sequence (list): List of event names
            
        Returns:
            list: List of (event, confidence) tuples
        """
        encoded = [self.event_to_id.get(event, 0) for event in event_sequence[-self.window_size:]]
        
        if len(encoded) < self.window_size:
            encoded = [0] * (self.window_size - len(encoded)) + encoded
        
        input_array = np.array([encoded])
        predictions = self.model.predict(input_array, verbose=0)
        
        predictions = predictions[0].reshape(-1, len(self.all_events))
        results = []
        
        for i in range(self.prediction_steps):
            probs = predictions[i]
            max_idx = np.argmax(probs)
            confidence = probs[max_idx]
            event_name = self.id_to_event.get(max_idx, 'UNKNOWN')
            results.append((event_name, float(confidence)))
        
        return results
    
    def evaluate(self, X_test, y_test):
        """
        Evaluate model on test set
        
        Args:
            X_test (np.array): Test input sequences
            y_test (np.array): Test target sequences
            
        Returns:
            dict: Evaluation metrics
        """
        y_pred = self.model.predict(X_test, verbose=0)
        
        # For classification, calculate accuracy
        y_pred_ids = np.argmax(y_pred, axis=-1)
        y_test_flat = y_test.flatten()
        y_pred_flat = y_pred_ids.flatten()
        
        accuracy = np.mean(y_pred_flat == y_test_flat)
        
        # Calculate per-step accuracy
        per_step_accuracy = []
        
        if self.prediction_steps == 1:
            # Single step prediction - y_pred_ids is 1D
            per_step_accuracy.append(accuracy)
        else:
            # Multi-step prediction - y_pred_ids is 2D
            for step in range(self.prediction_steps):
                if y_pred_ids.ndim > 1:
                    step_accuracy = np.mean(y_pred_ids[:, step] == y_test[:, step])
                else:
                    step_accuracy = accuracy
                per_step_accuracy.append(step_accuracy)
        
        metrics = {
            'overall_accuracy': accuracy,
            'per_step_accuracy': per_step_accuracy,
            'test_loss': float(self.model.evaluate(X_test, y_test, verbose=0)[0])
        }
        
        return metrics
    
    def save_model(self, model_dir):
        """
        Save model and metadata
        
        Args:
            model_dir (str): Directory to save model
        """
        model_dir = Path(model_dir)
        model_dir.mkdir(parents=True, exist_ok=True)
        
        # Save model
        self.model.save(str(model_dir / 'lstm_model.h5'))
        
        # Save metadata
        metadata = {
            'all_events': self.all_events,
            'event_to_id': self.event_to_id,
            'config': self.config,
            'window_size': self.window_size,
            'prediction_steps': self.prediction_steps
        }
        
        with open(model_dir / 'metadata.json', 'w') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"Model saved to {model_dir}")
    
    def load_model(self, model_dir):
        """
        Load model and metadata
        
        Args:
            model_dir (str): Directory containing saved model
        """
        model_dir = Path(model_dir)
        
        # Load model
        self.model = keras.models.load_model(str(model_dir / 'lstm_model.h5'))
        
        # Load metadata
        with open(model_dir / 'metadata.json', 'r') as f:
            metadata = json.load(f)
        
        self.all_events = metadata['all_events']
        self.event_to_id = metadata['event_to_id']
        self.id_to_event = {int(k): v for k, v in 
                            {v: k for k, v in metadata['event_to_id'].items()}.items()}
        self.config = metadata.get('config', {})
        self.window_size = metadata.get('window_size', 3)
        self.prediction_steps = metadata.get('prediction_steps', 1)
        
        print(f"Model loaded from {model_dir}")
