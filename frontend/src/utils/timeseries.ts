import type { DatabaseId } from '@/utils/navigation'

/**
 * Measured-response files that can accompany a record.
 *
 * Mirrors the subsidiary types the backend expands an `all-*` upload into
 * (`get_args_all` in `backend/resslab_hub/data/uploader.py`) and the column
 * requirements each one is validated against (`validate_one_file` in
 * `backend/resslab_hub/data/validator.py`).
 *
 * Two rules the UI has to respect:
 *  - the file must sit in `directory` inside the archive, and
 *  - its **filename is the foreign key**: `<specimen id>.csv`, matched against
 *    the `id` column of the primary CSV in the same archive.
 */
export interface TimeSeriesKind {
  /** Stable key, also the i18n suffix under `contribute.timeseries.kind`. */
  key: string
  /** Directory inside the archive, relative to the component root. */
  directory: string
  /** Columns the validator requires; every value must parse as a number. */
  requiredColumns: string[]
}

export const TIME_SERIES_KINDS: Partial<Record<DatabaseId, TimeSeriesKind[]>> = {
  braces: [
    {
      key: 'force_displacement',
      directory: 'braces/force_displacement',
      requiredColumns: ['Displacement [mm]', 'Force [kN]']
    }
  ],
  columns: [
    {
      key: 'axial_shortening',
      directory: 'columns/axial_shortening_rotation',
      requiredColumns: ['Chord Rotation [rads]', 'Axial Shortening [mm]']
    },
    {
      key: 'moment_strong',
      directory: 'columns/moment_rotation_strong',
      requiredColumns: ['Chord Rotation [rads]', 'Moment [kN-mm]']
    },
    {
      key: 'moment_weak',
      directory: 'columns/moment_rotation_weak',
      requiredColumns: ['Chord Rotation [rads]', 'Moment [kN-mm]']
    }
  ],
  connections: [
    {
      key: 'beam',
      directory: 'connections/Beam_moment_rotation',
      requiredColumns: ['Chord Rotation [rads]', 'Moment [kN-mm]']
    },
    {
      key: 'beam_west',
      directory: 'connections/Beam_moment_rotation_west',
      requiredColumns: ['Chord Rotation [rads]', 'Moment [kN-mm]']
    },
    {
      key: 'global',
      directory: 'connections/Global',
      requiredColumns: ['Total story drift angle (rad)', 'Force in the actuator (kN)']
    },
    {
      key: 'global_west',
      directory: 'connections/Global_west',
      requiredColumns: ['Total story drift angle (rad)', 'Force in the actuator (kN)']
    },
    {
      key: 'panel_zone',
      directory: 'connections/Panel_zone',
      requiredColumns: ['panel zone shear distortion (rad)', 'panel zone shear force (kN)']
    }
  ],
  hss: [
    {
      key: 'moment_rotation',
      directory: 'hss_columns/Moment_Rotation',
      requiredColumns: ['rotation (rad)', 'moment (kN.m)']
    }
  ],
  cyclic: [
    {
      key: 'stress_strain',
      directory: 'material/cyclic_coupons/stress_strain',
      requiredColumns: ['Sigma_true', 'e_true']
    }
  ],
  residuals: [
    {
      key: 'distribution_f1',
      directory: 'residual_stresses/Distributions/Distributions_F1',
      requiredColumns: ['coordinate', 'residual_stress']
    },
    {
      key: 'distribution_f2',
      directory: 'residual_stresses/Distributions/Distributions_F2',
      requiredColumns: ['coordinate', 'residual_stress']
    },
    {
      key: 'distribution_w1',
      directory: 'residual_stresses/Distributions/Distributions_W1',
      requiredColumns: ['coordinate', 'residual_stress']
    },
    {
      key: 'qp_coefficient',
      directory: 'residual_stresses/QP_Coefficients',
      requiredColumns: ['qp_coefficient']
    }
  ]
}

export function timeSeriesKindsFor(database: DatabaseId | null): TimeSeriesKind[] {
  return database ? TIME_SERIES_KINDS[database] ?? [] : []
}
