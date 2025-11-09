# database.py
import csv
import pathlib
from typing import List, Dict
from datetime import datetime

class UserDatabase:
    def __init__(self, data_dir: pathlib.Path):
        self.data_dir = data_dir
    
    def get_user_file(self, username: str) -> pathlib.Path:
        return self.data_dir / f"{username.lower()}_workouts.csv"
    
    def create_user_file(self, username: str):
        file_path = self.get_user_file(username)
        if not file_path.exists():
            with open(file_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["timestamp", "exercise", "reps", "sets", "duration_min", "valid_reps"])
    
    def record_workout(self, username: str, exercise: str, reps: int, 
                      sets: int, duration: float, valid_reps: int):
        """Record workout with tempo-validated reps"""
        self.create_user_file(username)
        
        file_path = self.get_user_file(username)
        with open(file_path, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.now().isoformat(),
                exercise,
                reps,
                sets,
                f"{duration:.1f}",
                valid_reps
            ])
    
    def get_workout_history(self, username: str) -> List[Dict]:
        file_path = self.get_user_file(username)
        if not file_path.exists():
            return []
        
        history = []
        with open(file_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                history.append(row)
        return history
    
    def get_total_stats(self, username: str) -> Dict:
        history = self.get_workout_history(username)
        if not history:
            return {"total_workouts": 0, "total_reps": 0, "avg_accuracy": 0}

        total_workouts = len(history)
        total_reps = 0
        total_accuracy = 0
        valid_entries = 0

        for row in history:
            try:
                reps = int(row.get("reps", 0))
                sets = int(row.get("sets", 1))
                valid_reps = int(row.get("valid_reps", reps * sets))

                total_reps += reps * sets
                accuracy = (valid_reps / (reps * sets) * 100) if (reps * sets) > 0 else 100
                total_accuracy += accuracy
                valid_entries += 1
            except (ValueError, KeyError, ZeroDivisionError) as e:
                # Skip invalid rows
                print(f"Warning: Skipping invalid workout row: {e}")
                continue

        avg_accuracy = total_accuracy / valid_entries if valid_entries > 0 else 0

        return {
            "total_workouts": valid_entries,
            "total_reps": total_reps,
            "avg_accuracy": round(avg_accuracy, 1)
        }