# miner_manager.py
import json
from PyQt5.QtWidgets import QMessageBox

class MinerManager:
    @staticmethod
    def load_miners():
        try:
            with open("miners.json", "r") as f:
                data = json.load(f)
                return data.get("miners", []) if isinstance(data, dict) else data
        except:
            return []
    
    @staticmethod
    def save_miners(miners):
        with open("miners.json", "w") as f:
            json.dump({"miners": miners}, f, indent=4)
    
    def add_miner(self, miner_id, parent):
        if not miner_id:
            QMessageBox.warning(parent, "Warning", "Please enter a miner address")
            return False
            
        miners = self.load_miners()
        
        if miner_id in miners:
            QMessageBox.warning(parent, "Warning", "Miner already exists")
            return False
            
        miners.append(miner_id)
        self.save_miners(miners)
        QMessageBox.information(parent, "Success", "Miner added successfully.")
        return True
    
    def remove_miner(self, miner_id, parent):
        if not miner_id:
            QMessageBox.warning(parent, "Warning", "Please enter a miner address")
            return False
            
        miners = self.load_miners()
        
        if miner_id not in miners:
            QMessageBox.warning(parent, "Warning", "Miner not found in list")
            return False
            
        reply = QMessageBox.question(
            parent, 
            "Confirm Removal",
            f"Are you sure you want to remove miner: {miner_id}?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            miners.remove(miner_id)
            self.save_miners(miners)
            QMessageBox.information(parent, "Success", "Miner removed successfully.")
            return True
            
        return False