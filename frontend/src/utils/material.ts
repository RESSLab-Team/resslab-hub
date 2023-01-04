import { clone, fill, sum, zip } from "lodash";

/**
 * https://github.com/ahartloper/RESSPyLab/blob/master/RESSPyLab/uvc_model.py
 */
export function computeUvc(
  eTrue: number[],
  sigmaTrue: number[],
  E: number,
  sy_0: number,
  Q: number,
  b: number,
  D: number,
  a: number,
  ks: { c: number; gamma: number }[],
  tol = 1.0e-8,
  maximum_iterations = 1000
): {
  stress: number[];
  strain: number[];
  error: number;
  num_its: number[];
  area: number;
} {
  const alpha_components = fill(Array(ks.length), 0);
  let strain = 0;
  let stress = 0;
  let ep_eq = 0;

  let error = 0; // error measure
  let sum_abs_de = 0; // total strain
  let stress_sim = 0.0;
  let stress_test = 0.0;
  let area_test = 0.0;

  const stress_track: number[] = [];
  const strain_track: number[] = [];
  const strain_inc_track: number[] = [];
  const iteration_track: number[] = [];

  const loading = discreteDifference(eTrue);
  loading.forEach((strain_inc, increment_number) => {
    strain += strain_inc;
    const alpha = sum(alpha_components);
    const yield_stress =
      sy_0 + Q * (1 - Math.exp(-b * ep_eq)) - D * (1 - Math.exp(-a * ep_eq));

    const trial_stress = stress + E * strain_inc;
    const relative_stress = trial_stress - alpha;
    const flow_dir = Math.sign(relative_stress);

    const yield_condition = Math.abs(relative_stress) - yield_stress;
    let is_converged = yield_condition > tol;

    // For error
    const stress_sim_1 = stress_sim * 1.0;
    const stress_test_1 = stress_test * 1.0;

    // Return mapping if plastic loading
    const ep_eq_init = ep_eq;
    const alpha_init = alpha;
    let consist_param = 0;
    let number_of_iterations = 0;
    while (!is_converged && number_of_iterations < maximum_iterations) {
      number_of_iterations += 1;
      // Isotropic hardening and isotropic modulus
      const yield_stress =
        sy_0 + Q * (1 - Math.exp(-b * ep_eq)) - D * (1 - Math.exp(-a * ep_eq));
      const iso_modulus =
        Q * b * Math.exp(-b * ep_eq) - D * a * Math.exp(-a * ep_eq);

      // Kinematic hardening and kinematic modulus
      let alpha = 0;
      let kin_modulus = 0;
      ks.forEach((k, i) => {
        const e_k = Math.exp(-k.gamma * (ep_eq - ep_eq_init));
        alpha +=
          (flow_dir * k.c) / k.gamma +
          (alpha_components[i] - (flow_dir * k.c) / k.gamma) * e_k;
        kin_modulus +=
          k.c * e_k - flow_dir * k.gamma * e_k * alpha_components[i];
      });
      const delta_alpha = alpha - alpha_init;

      // Local Newton step
      const numerator =
        Math.abs(relative_stress) -
        (consist_param * E + yield_stress + flow_dir * delta_alpha);
      const denominator = -(E + iso_modulus + kin_modulus);
      consist_param = consist_param - numerator / denominator;
      ep_eq = ep_eq_init + consist_param;

      if (Math.abs(numerator) < tol) {
        is_converged = true;
      }
    }

    // Update the variables
    stress = trial_stress - E * flow_dir * consist_param;
    ks.forEach((k, i) => {
      const e_k = Math.exp(-k.gamma * (ep_eq - ep_eq_init));
      alpha_components[i] =
        (flow_dir * k.c) / k.gamma +
        (alpha_components[i] - (flow_dir * k.c) / k.gamma) * e_k;
    });

    stress_track.push(stress);
    strain_track.push(strain);
    strain_inc_track.push(strain_inc);
    iteration_track.push(number_of_iterations);

    // Calculate the error
    stress_sim = stress * 1.0;
    stress_test = sigmaTrue[increment_number];

    sum_abs_de += Math.abs(strain_inc);
    area_test +=
      (Math.abs(strain_inc) *
        (Math.pow(stress_test, 2) + Math.pow(stress_test_1, 2))) /
      2;
    error +=
      (Math.abs(strain_inc) *
        (Math.pow(stress_sim - stress_test, 2) +
          Math.pow(stress_sim_1 - stress_test_1, 2))) /
      2;

    if (number_of_iterations >= maximum_iterations) {
      throw new Error(
        `Return mapping did not converge in ${maximum_iterations} iterations.`
      );
    }
  });

  const area = area_test / sum_abs_de;
  error = error / sum_abs_de;
  return {
    stress: stress_track,
    strain: strain_track,
    error: error,
    num_its: iteration_track,
    area: area,
  };
}

/**
 * https://numpy.org/doc/stable/reference/generated/numpy.diff.html
 */
function discreteDifference(a: number[]): number[] {
  const values = clone(a);
  values.shift();
  return zip(a, values).flatMap(([a, b]) =>
    a !== undefined && b !== undefined ? [b - a] : []
  );
}
