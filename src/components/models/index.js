import PlaceValueModel from './PlaceValueModel'
import NumberLineModel from './NumberLineModel'
import FractionStripModel from './FractionStripModel'
import FactorArrayModel from './FactorArrayModel'
import AreaPerimeterModel from './AreaPerimeterModel'

/** Component key → the model itself, so the catalogue can stay data. */
export const MODEL_COMPONENTS = {
  'place-value': PlaceValueModel,
  'number-line': NumberLineModel,
  'fraction-strips': FractionStripModel,
  'factor-arrays': FactorArrayModel,
  'area-perimeter': AreaPerimeterModel,
}
