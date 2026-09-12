"""Tooling for building and checking the question bank.

- :mod:`.taxonomy`   - the content domains and skills of the Digital SAT
- :mod:`.blueprint`  - the module structure from ``SAT test structure/``
- :mod:`.schema`     - validation rules for a bank file
- :mod:`.importer`   - normalise an export you already have on disk
- :mod:`.generator`  - build original questions from this project's templates
- :mod:`.assembler`  - turn a pool of questions into module bundles
- :mod:`.ordering`   - the order questions run in inside a module
- :mod:`.export`     - render the bank as readable papers and answer keys
"""

from .assembler import AssemblyError, BundleSpec, ModuleSpec, Slot, assemble_bank, default_spec
from .blueprint import BlueprintError
from .export import export_bank
from .generator import GenerationError, generate_bank, generate_questions
from .importer import import_questions, load_source
from .ordering import exam_order, is_exam_order, order_bank
from .schema import BankValidationError, Issue, assert_valid, summarise, validate_bank

__all__ = [
    "AssemblyError",
    "BankValidationError",
    "BlueprintError",
    "BundleSpec",
    "GenerationError",
    "Issue",
    "ModuleSpec",
    "Slot",
    "assemble_bank",
    "assert_valid",
    "default_spec",
    "exam_order",
    "export_bank",
    "generate_bank",
    "generate_questions",
    "import_questions",
    "is_exam_order",
    "load_source",
    "order_bank",
    "summarise",
    "validate_bank",
]
