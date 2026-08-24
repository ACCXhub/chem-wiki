from chem_wiki.modules.structure_lab import StructureAnalysis, StructureInput, analyze_structure


class RecordingEngine:
    def __init__(self) -> None:
        self.received: StructureInput | None = None

    def analyze(self, structure: StructureInput) -> StructureAnalysis:
        self.received = structure
        return StructureAnalysis(
            state="unsupported",
            input_format=structure.format,
            code="test_engine",
        )


def test_application_contract_accepts_an_engine_without_library_objects() -> None:
    engine = RecordingEngine()

    result = analyze_structure(input_format=" SMILES ", text="CCO", engine=engine)

    assert engine.received == StructureInput(format="smiles", text="CCO")
    assert result.state == "unsupported"
    assert result.code == "test_engine"
