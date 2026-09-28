from abc import ABC,abstractmethod
from .ai_rules import evaluate,score

class DiagnosticProvider(ABC):
    """Extension boundary. Implementations must disclose whether data leaves device."""
    sends_data=False
    @abstractmethod
    def analyze(self,metrics):raise NotImplementedError

class LocalProvider(DiagnosticProvider):
    def analyze(self,metrics):
        alerts=evaluate(metrics)
        return {'mode':'LOCAL MODE','data_leaves_device':False,'metrics':metrics,'alerts':alerts,'risk_score':score(alerts),
                'coverage':'Rozpoznane metryki: '+str(len(metrics)),'note':'Brak alertu nie gwarantuje sprawności ani bezpieczeństwa. Program niczego nie naprawia.'}
