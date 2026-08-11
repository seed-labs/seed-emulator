#!/usr/bin/env python3
"""
Base class for AI Agents that diagnose emulator faults.

This module provides the interface and common functionality
for all AI agent implementations.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
import subprocess
import json


@dataclass
class Diagnosis:
    """Structured diagnosis result."""
    category: str
    root_cause: str
    symptoms: List[str]
    proposed_fix: str
    confidence: float
    reasoning: str = ""
    commands_executed: List[str] = field(default_factory=list)
    raw_outputs: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category,
            "root_cause": self.root_cause,
            "symptoms": self.symptoms,
            "proposed_fix": self.proposed_fix,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "commands_executed": self.commands_executed,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


class BaseDiagnosticAgent(ABC):
    """Base class for diagnostic AI agents."""

    def __init__(self, name: str):
        self.name = name
        self.commands_executed = []
        self.outputs = {}

    def run_command(self, command: str, timeout: int = 30) -> str:
        """Execute a command and return output."""
        try:
            result = subprocess.run(
                command.split(),
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            output = result.stdout + result.stderr
            self.commands_executed.append(command)
            self.outputs[command] = output
            return output
        except subprocess.TimeoutExpired:
            return "Command timed out"
        except Exception as e:
            return f"Error: {str(e)}"

    def check_container_status(self, container_name: str) -> Dict[str, str]:
        """Check container status."""
        cmd = f"docker inspect --format '{{{{.State.Status}}}}' {container_name}"
        status = self.run_command(cmd).strip()

        cmd = f"docker inspect --format '{{{{.State.StartedAt}}}}' {container_name}"
        started = self.run_command(cmd).strip()

        return {
            "name": container_name,
            "status": status,
            "started": started,
        }

    def get_bgp_summary(self, container_name: str) -> str:
        """Get BGP protocol summary."""
        return self.run_command(f"docker exec {container_name} birdc show protocols")

    def get_bgp_details(self, container_name: str) -> str:
        """Get detailed BGP protocol information."""
        return self.run_command(f"docker exec {container_name} birdc show protocols all")

    def get_routing_table(self, container_name: str) -> str:
        """Get routing table."""
        return self.run_command(f"docker exec {container_name} ip route show")

    def get_bgp_routes(self, container_name: str) -> str:
        """Get BGP routes."""
        return self.run_command(f"docker exec {container_name} birdc show route")

    def test_connectivity(self, source_container: str, target_ip: str) -> bool:
        """Test connectivity between containers."""
        output = self.run_command(
            f"docker exec {source_container} ping -c 2 {target_ip}"
        )
        return "0% packet loss" in output

    def get_logs(self, container_name: str, lines: int = 50) -> str:
        """Get container logs."""
        return self.run_command(f"docker logs --tail {lines} {container_name}")

    @abstractmethod
    def diagnose(self, scenario_hint: str = None) -> Diagnosis:
        """
        Diagnose the fault in the emulator.

        Args:
            scenario_hint: Optional hint about the scenario type

        Returns:
            Diagnosis object with findings
        """
        pass

    def reset(self):
        """Reset agent state for new diagnosis."""
        self.commands_executed = []
        self.outputs = {}


class DiagnosticAgentRunner:
    """Runner for executing and evaluating diagnostic agents."""

    def __init__(self, agent: BaseDiagnosticAgent):
        self.agent = agent
        self.results = []

    def run_scenario(
        self,
        scenario_name: str,
        ground_truth: Dict[str, Any],
        containers: Dict[str, str] = None,
    ) -> Dict[str, Any]:
        """
        Run agent on a scenario and evaluate results.

        Args:
            scenario_name: Name of the scenario
            ground_truth: Expected diagnosis
            containers: Container name mappings

        Returns:
            Evaluation results
        """
        print(f"\n{'='*60}")
        print(f"Running agent '{self.agent.name}' on scenario: {scenario_name}")
        print(f"{'='*60}")

        # Reset agent state
        self.agent.reset()

        # Run diagnosis
        start_time = datetime.now()
        diagnosis = self.agent.diagnose(scenario_name)
        end_time = datetime.now()

        # Evaluate
        evaluation = self._evaluate(diagnosis, ground_truth)

        # Add metadata
        evaluation['scenario'] = scenario_name
        evaluation['agent'] = self.agent.name
        evaluation['duration_seconds'] = (end_time - start_time).total_seconds()
        evaluation['commands_executed'] = len(self.agent.commands_executed)
        evaluation['diagnosis'] = diagnosis.to_dict()

        self.results.append(evaluation)

        # Print summary
        self._print_evaluation(evaluation)

        return evaluation

    def _evaluate(
        self,
        diagnosis: Diagnosis,
        ground_truth: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Evaluate diagnosis against ground truth."""

        # Category match
        category_correct = diagnosis.category == ground_truth.get('category')

        # Root cause similarity (simple substring match)
        gt_cause = ground_truth.get('root_cause', '').lower()
        agent_cause = diagnosis.root_cause.lower()
        cause_correct = gt_cause in agent_cause or agent_cause in gt_cause

        # Symptom match
        gt_symptoms = set(s.lower() for s in ground_truth.get('symptoms', []))
        agent_symptoms = set(s.lower() for s in diagnosis.symptoms)
        symptoms_matched = len(gt_symptoms & agent_symptoms)
        symptoms_total = len(gt_symptoms)

        # Overall accuracy
        if category_correct and cause_correct:
            accuracy = 'exact'
        elif category_correct:
            accuracy = 'category'
        elif symptoms_matched > 0:
            accuracy = 'partial'
        else:
            accuracy = 'wrong'

        return {
            'accuracy': accuracy,
            'category_correct': category_correct,
            'cause_correct': cause_correct,
            'symptoms_matched': symptoms_matched,
            'symptoms_total': symptoms_total,
            'confidence': diagnosis.confidence,
        }

    def _print_evaluation(self, evaluation: Dict[str, Any]):
        """Print evaluation summary."""
        print(f"\nEvaluation Results:")
        print(f"  Accuracy: {evaluation['accuracy']}")
        print(f"  Category Correct: {'✓' if evaluation['category_correct'] else '✗'}")
        print(f"  Cause Correct: {'✓' if evaluation['cause_correct'] else '✗'}")
        print(f"  Symptoms: {evaluation['symptoms_matched']}/{evaluation['symptoms_total']}")
        print(f"  Confidence: {evaluation['confidence']:.0%}")
        print(f"  Commands: {evaluation['commands_executed']}")
        print(f"  Duration: {evaluation['duration_seconds']:.1f}s")

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all results."""
        if not self.results:
            return {}

        total = len(self.results)
        exact = sum(1 for r in self.results if r['accuracy'] == 'exact')
        category = sum(1 for r in self.results if r['accuracy'] == 'category')
        partial = sum(1 for r in self.results if r['accuracy'] == 'partial')
        wrong = sum(1 for r in self.results if r['accuracy'] == 'wrong')

        return {
            'agent': self.agent.name,
            'total_scenarios': total,
            'exact': exact,
            'category': category,
            'partial': partial,
            'wrong': wrong,
            'accuracy_rate': (exact + category) / total if total > 0 else 0,
            'avg_commands': sum(r['commands_executed'] for r in self.results) / total,
            'avg_duration': sum(r['duration_seconds'] for r in self.results) / total,
        }
