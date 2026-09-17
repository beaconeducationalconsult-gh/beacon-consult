import { registry } from '../kernel'
import { MathModule } from './math/MathModule'
import { EnglishModule } from './english/EnglishModule'
import { ScienceModule } from './science/ScienceModule'
import { SocialStudiesModule } from './social-studies/SocialStudiesModule'
import { HistoryModule } from './history/HistoryModule'
import { RMEModule } from './rme/RMEModule'
import { GhanaianLanguageModule } from './ghanaian-language/GhanaianLanguageModule'
import { ComputingModule } from './computing/ComputingModule'
import { CareerTechnologyModule } from './career-technology/CareerTechnologyModule'
import { FrenchModule } from './french/FrenchModule'
import { CreativeArtsModule } from './creative-arts/CreativeArtsModule'
import { CreativeArtsDesignModule } from './creative-arts-design/CreativeArtsDesignModule'
import { OWOPModule } from './owop/OWOPModule'

registry.register(new MathModule())
registry.register(new EnglishModule())
registry.register(new ScienceModule())
registry.register(new SocialStudiesModule())
registry.register(new HistoryModule())
registry.register(new RMEModule())
registry.register(new GhanaianLanguageModule())
registry.register(new ComputingModule())
registry.register(new CareerTechnologyModule())
registry.register(new FrenchModule())
registry.register(new CreativeArtsModule())
registry.register(new CreativeArtsDesignModule())
registry.register(new OWOPModule())
