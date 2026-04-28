<script setup lang="ts">
import {
  getBraceImage,
  getColumnMapImage,
  getConnectionSpecimenImage,
  getResidualStressImage,
  getSteelMaterialImage,
  getEbfImage
} from '@/utils/component'
import { testConfigurationNameMapping } from '@/utils/hss'

const { data, type } = defineProps<{
  data: any
  type: string
}>()
</script>

<template>
  <div class="tooltip">
    <template v-if="type === 'Connections'">
      <h3>
        <a target="_blank" :href="data.link"> {{ data.experimental_program }} ({{ data.date }}) </a>
      </h3>
      <ul>
        <li>{{ data.specimen_type }}</li>
        <li>{{ data.connection_type }}, Beam: {{ data.section_b }} Col: {{ data.section_c }}</li>
        <li>
          <img :alt="data.specimen_type" :src="getConnectionSpecimenImage(data.specimen_type)" />
        </li>
        <li>
          <a :href="`/connections/database?id=${data.id}&detail=true`"> View experimental data </a>
        </li>
      </ul>
    </template>
    <template v-else-if="type === 'Braces'">
      <h3>
        <a target="_blank" :href="data.link"> {{ data.investigator }} ({{ data.date }}) </a>
      </h3>
      <ul>
        <li>Cross section: {{ data.cross_section_size }}</li>
        <li>KL/r: {{ data.kl_r }}</li>
        <li>
          <img alt="Brace image" :src="getBraceImage(data.boundary_condition)" />
        </li>
        <li>
          <a :href="`/braces/database?id=${data.id}&detail=true`"> View experimental data </a>
        </li>
      </ul>
    </template>
    <template v-else-if="type === 'Columns'">
      <h3>
        <a target="_blank" :href="data.link"> {{ data.experimental_program }} ({{ data.date }}) </a>
      </h3>
      <ul>
        <li>{{ data.boundary_condition }}</li>
        <li>
          {{ data.axial_lp }} (Pg/Py = {{ data.p_g_over_p_ym }}), Column: {{ data.section_c }}
        </li>
        <li>
          <img
            alt="Column image"
            :src="getColumnMapImage(data.axis_of_bending, data.boundary_condition)"
          />
        </li>
        <li>
          <a :href="`/columns/database?id=${data.id}&detail=true`"> View experimental data </a>
        </li>
      </ul>
    </template>
    <template v-else-if="type === 'Materials'">
      <h3>
        <a target="_blank" :href="data.link"> {{ data.experimental_program }} ({{ data.date }}) </a>
      </h3>
      <ul>
        <li>Profile type: {{ data.profile_type }}</li>
        <li>Cross section: {{ data.profile }}</li>
        <li>
          <img alt="Material image" :src="getSteelMaterialImage()" />
        </li>
        <li>
          <a :href="`/materials/cyclic-coupons?id=${data.id}&detail=true`"> View experimental data </a>
        </li>
      </ul>
    </template>
    <template v-else-if="type === 'Residual Stresses'">
      <h3>
        <a target="_blank" :href="data.link"> {{ data.experimental_program }} ({{ data.date }}) </a>
      </h3>
      <ul>
        <li>Profile type: {{ data.profile_type }}</li>
        <li>Cross section: {{ data.profile }}</li>
        <li>
          <img alt="Residual stress image" :src="getResidualStressImage()" />
        </li>
        <li>
          <a :href="`/residuals/database?id=${data.id}&detail=true`"> View experimental data </a>
        </li>
      </ul>
    </template>
    <template v-else-if="type === 'HSS Columns'">
      <h3>
        <a target="_blank" :href="data.url"> {{ data.investigator }} ({{ data.date }}) </a>
      </h3>
      <ul>
        <li>Test configuration: {{ testConfigurationNameMapping.get(data.test_configuration) }}</li>
        <li>Tube section: {{ data.tube_section }}</li>
        <li>
          <img alt="HSS Column image" src="/img/hss/hss_tooltip.png" />
        </li>
        <li>
          <a :href="`/hss-columns/database?id=${data.id}&detail=true`"> View experimental data </a>
        </li>
      </ul>
    </template>
    <template v-else-if="type === 'EBF Links'">
      <h3>
        <a target="_blank" :href="data.url"> {{ data.investigator }} ({{ data.year }}) </a>
      </h3>
      <ul>
        <li><strong>Specimen ID:</strong> {{ data.spec_id }}</li>
        <li><strong>Profile:</strong> {{ data.profile }}</li>
        <li><strong>Link Location:</strong> {{ data.link_loc }}</li>
        <li><strong>Link Length:</strong> {{ data.e }} mm</li>
        <li><strong>Section Type:</strong> {{ data.sec_type }}</li>
        <li><strong>Classification:</strong> {{ data.class_aisc }}</li>
        <li>
          <img alt="EBF Link Configuration" :src="getEbfImage(data.l_confi)" />
        </li>
        <li>
          <a :href="`/ebf-links/database?id=${data.id}&detail=true`"> View experimental data </a>
        </li>
      </ul>
    </template>
    <template v-else>
      <h3>No tooltip available for type "{{ type }}"</h3>
    </template>
  </div>
</template>

<style scoped>
.tooltip {
  padding: 10px;
  font-family: Arial, sans-serif;
}
.tooltip h3 {
  margin: 0;
  font-size: 1.1em;
}
.tooltip ul {
  padding-left: 1em;
  list-style-type: none;
  margin: 5px 0;
}
.tooltip li {
  margin-bottom: 0.5em;
}
.tooltip img {
  max-width: 100%;
  height: auto;
}
</style>
