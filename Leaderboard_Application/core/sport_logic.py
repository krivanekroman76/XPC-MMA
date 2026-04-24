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
            
        # Add penalty time (converted from seconds to milliseconds)
        final_time = max_time + (penalty_seconds * 1000)
        return final_time

    def get_best_time(self, attempts_data):
        # Filter out 0 (not run yet) and 999999 (Invalid/NP)
        valid_times = [a.get("final_time", 0) for a in attempts_data if 0 < a.get("final_time", 0) < 999999]
        
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
    def calculate_attempt_time(self, sections_data):
        """
        Očekává data z GUI ve formátu např:
        sections_data = [
            {"time": 16.5, "penalty_seconds": 0, "np_reason": None},  # Úsek 1
            {"time": 17.2, "penalty_seconds": 2, "np_reason": None},  # Úsek 2
            {"time": 0,    "penalty_seconds": 0, "np_reason": "Ztráta náčiní"} # Úsek 3
        ]
        """
        total_time = 0
        
        for section in sections_data:
            # Pokud má jakýkoliv úsek NP, celý pokus je obvykle NP
            if section.get("np_reason"):
                # Můžeme zde rovnou vrátit 999999 nebo odeslat zprávu
                print(f"Pokus neplatný! Důvod: {section['np_reason']}")
                return 999999
                
            total_time += section.get("time", 0) + section.get("penalty_seconds", 0)
            
        return total_time

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