"""NCOS — NaCCA Curriculum Operating System.

kernel/   the curriculum engine: interface contract, module registry, drivers
modules/  subject modules — one directory per subject, each implementing
          the SubjectModule interface defined in kernel/interface.py
service/  the Material Service — the "syscall" boundary the Portal talks to
"""
__version__ = "0.1.0"
