"""Tooling for building and checking the question bank.

- :mod:`.schema`     - validation rules for a bank file
- :mod:`.importer`   - normalise an export you already have on disk
- :mod:`.generator`  - build original questions from this project's templates
- :mod:`.assembler`  - turn a pool of questions into module bundles
"""

from .assembler import AssemblyError, BundleSpec, ModuleSpec, assemble_bank, default_spec
from .generator import GenerationError, generate_bank, generate_questions
from .importer import import_questions, load_source
from .schema import BankValidationError, Issue, assert_valid, summarise, validate_bank

__all__ = [
    "AssemblyError",
    "BankValidationError",
    "BundleSpec",
    "GenerationError",
    "Issue",
    "ModuleSpec",
    "assemble_bank",
    "assert_valid",
    "default_spec",
    "generate_bank",
    "generate_questions",
    "import_questions",
    "load_source",
    "summarise",
    "validate_bank",
]
