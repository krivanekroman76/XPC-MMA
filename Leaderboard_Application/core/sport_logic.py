class BaseSport:
    """
    Base logic class for all sports.
    Handles standard time calculations and penalties.
    """
    def calculate_attempt_time(self, lanes_dict, penalty_seconds=0):
        # If no times are recorded yet, return 0
        if not lanes_dict:
            return 0
            
        # The final time is usually determined by the last target hit
        max_time = max(lanes_dict.values())
        
        # Check for Invalid Attempt (NP) represented by 999999
        if max_time >= 999999:
            return 999999
            
        # FIXED: Removed the * 1000 since max_time is already in seconds
        final_time = max_time + penalty_seconds
        return final_time

    def get_best_time(self, attempts_data):
        # Filter out 0 (not run yet), 999999 (Invalid/NP), and None values
        valid_times = [
            a.get("final_time") 
            for a in attempts_data 
            if a.get("final_time") is not None and 0 < a.get("final_time") < 999999
        ]
        
        if not valid_times:
            return 999999 # NP or no valid times yet
            
        return min(valid_times)


class FireAttackLogic(BaseSport):
    """
    Specific rules for Fire Attack (Požární útok).
    Currently uses standard base logic, but ready for future specifics.
    """
    pass

class RelayLogic(BaseSport):
    # FIXED: Signature updated to match BaseSport and what the GUI sends
    def calculate_attempt_time(self, sections_data, penalty_seconds=0):
        """
        Očekává data z GUI ve formátu např:
        sections_data = [
            {"time": 16.5, "penalty_seconds": 0, "np_reason": None},  # Úsek 1
            {"time": 17.2, "penalty_seconds": 2, "np_reason": None},  # Úsek 2
            {"time": 0,    "penalty_seconds": 0, "np_reason": "Ztráta náčiní"} # Úsek 3
        ]
        """
        total_time = 0
        
        # Note: If the GUI passes a dictionary like {"L1": 16.5} instead of 
        # a list of sections, you will need to adapt this logic to handle dictionaries!
        
        # Check if sections_data is a list (Relay format) or dict (Standard format)
        if isinstance(sections_data, dict):
            # Fallback if standard GUI calls RelayLogic with standard lanes_dict
            return super().calculate_attempt_time(sections_data, penalty_seconds)

        for section in sections_data:
            # Pokud má jakýkoliv úsek NP, celý pokus je obvykle NP
            if section.get("np_reason"):
                print(f"Pokus neplatný! Důvod: {section['np_reason']}")
                return 999999
                
            total_time += section.get("time", 0) + section.get("penalty_seconds", 0)
            
        return total_time + penalty_seconds

class TfaLogic(BaseSport):
    """
    Specific rules for TFA.
    """
    pass

def get_sport_logic(base_logic_name):
    """
    Factory function to return the correct calculation module.
    The string must match the 'base_logic' value in sport_presets.json.
    """
    if base_logic_name == "relay":
        return RelayLogic()
    elif base_logic_name == "tfa":
        return TfaLogic()
    elif base_logic_name == "attack":
        return FireAttackLogic()
    else:
        return BaseSport() # Bezpečnostní pojistka, kdyby tam v JSONu byl překlep