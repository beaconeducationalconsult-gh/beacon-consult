// app/src/kernel/registry.ts
import type { SubjectModule } from './SubjectModule'

export interface BootEntry {
  moduleId: string
  ok: boolean
  detail: string
}

export interface BootReport {
  loaded: string[]
  failed: BootEntry[]
  durationMs: number
}

class ModuleRegistry {
  private modules = new Map<string, SubjectModule>()
  bootReport: BootReport = { loaded: [], failed: [], durationMs: 0 }

  register(module: SubjectModule): void {
    const t0 = performance.now()
    const problems = module.validate()
    if (problems.length > 0) {
      this.bootReport.failed.push({
        moduleId: module.id,
        ok: false,
        detail: problems.join('; '),
      })
      console.warn(`[registry] ${module.id} failed validation:`, problems)
    } else {
      this.modules.set(module.id, module)
      this.bootReport.loaded.push(module.id)
    }
    this.bootReport.durationMs += performance.now() - t0
  }

  get(subjectId: string): SubjectModule {
    const m = this.modules.get(subjectId)
    if (!m) throw new Error(`'${subjectId}' is not loaded — check boot report`)
    return m
  }

  capableOf(subjectId: string, capability: string): boolean {
    return this.modules.get(subjectId)?.capabilities.has(capability) ?? false
  }

  listLoaded(): string[] {
    return [...this.modules.keys()]
  }
}

// Singleton — import this everywhere
export const registry = new ModuleRegistry()