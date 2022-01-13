<template>
  <v-container class="text-justify">
    <v-img src="resslab_logo_v1.svg" contain max-height="128"></v-img>
    <h1>Introduction</h1>
    <p>
      Advancements in the design, assessment and retrofitting of structures
      subjected to earthquake loading enable the use of Performance-Based
      Earthquake Engineering (PBEE). This methodology utilizes simulation models
      that explicitly predict the nonlinear behavior of structural components
      from the onset of damage to structural collapse. Experimental data across
      scales enable the further development and validation of multi-fidelity
      simulation models and inform uncertainty quantification to enable PBEE.
      Recent developments in PBEE enable studies from the building to urban
      scale for benchmarking the seismic performance of infrastructure systems,
      the further development of codes and standards, among others, to minimize
      the impacts of earthquakes worldwide. Moreover, digitalization of our
      cities requires the use of standardized predictive models for maintenance
      and life-cycle assessment of infrastructure systems.
    </p>
    <p>
      Within such a context, the RESSLab-hub provides open-access to the
      engineering and research communities to material and structural
      performance databases along with state-of-the-art modeling with the
      overarching goal to advance knowledge for minimizing the earthquake risk
      of steel and composite-steel concrete structures.
    </p>
    <h1>Databases</h1>
    <p>
      A series of material and structural performance databases have been
      developed with enhanced visualization features for efficient search and
      data exploitation. The databases provide access to physical experiments of
      a rich set of structural steel materials, structural components and
      connections that were tested worldwide since the 1970s. In particular, the
      databases include the following information:
    </p>
    <ul>
      <li>Parallel axis search and visualization capabilities</li>
      <li>Complete reference of the experimental report</li>
      <li>
        Test configuration and detailed description of geometric properties
      </li>
      <li>Nominal and measured material properties</li>
      <li>Design parameters of interest</li>
      <li>
        Fully digitized load deformation/deduced moment rotation /panel zone
        shear distortion depending on the structural component of interest
        (whichever is available)
      </li>
    </ul>
    <br />
    <p>
      Salient features of the assembled structural component databases have been
      presented in prior published work as follows:
    </p>
    <ul>
      <li>
        Beam-to-column connections (<a
          href="https://ascelibrary.org/doi/full/10.1061/%28ASCE%29ST.1943-541X.0000646"
          target="_blank"
          >Lignos and Krawinkler 2013</a
        >,
        <a
          href="https://link.springer.com/article/10.1007/s10518-019-00564-w"
          target="_blank"
          >El Jisr et al. 2019</a
        >,
        <a
          href="https://ascelibrary.org/doi/full/10.1061/%28ASCE%29ST.1943-541X.0002957"
          target="_blank"
          >Skiadopoulos et al. 2021</a
        >).
      </li>
      <li>
        Steel columns (<a
          href="https://ascelibrary.org/doi/full/10.1061/(ASCE)ST.1943-541X.0001937"
          target="_blank"
          >Elkady and Lignos 2018</a
        >,
        <a
          href="https://ascelibrary.org/doi/full/10.1061/%28ASCE%29ST.1943-541X.0002499"
          target="_blank"
          >Cravero et al. 2021</a
        >).
      </li>
    </ul>
    <br />
    <h1>Component Models</h1>
    <p>
      This web-based interactive tool allows the user to automatically construct
      backbone and first-cycle envelope curves for structural steel components,
      within the framework of concentrated plasticity, for direct use in
      nonlinear static and dynamic analyses procedures. Besides the use of
      built-up cross sections, it links with currently available cross-sectional
      databases from North America, Europe and Japan to extract geometric
      features from standardized hot-rolled profiles, which are currently used
      in steel construction worldwide. The backbone and first-cycle envelope
      curves are based on the following published work:
    </p>
    <ul>
      <li>
        Steel beams (<a
          href="https://ascelibrary.org/doi/full/10.1061/%28ASCE%29ST.1943-541X.0000376"
          target="_blank"
          >Lignos and Krawinkler 2011</a
        >).
      </li>
      <li>
        Pre-Northridge steel beam-to-column connections (<a
          href="https://www.sciencedirect.com/science/article/pii/S0141029612003689"
          target="_blank"
          >Ramirez et al. 2012</a
        >).
      </li>
      <li>
        Steel wide-flange (H-shaped) columns (<a
          href="https://journals.sagepub.com/doi/full/10.1193/122017EQS260M"
          target="_blank"
          >Elkady et al. 2019</a
        >).
      </li>
    </ul>
    <br />
    <h1>Future Updates</h1>
    <p>
      Other web-based interactive tools for various structural components are
      currently under development. Stay tuned for future updates of both
      datasets and developed tools.
    </p>
  </v-container>
</template>
