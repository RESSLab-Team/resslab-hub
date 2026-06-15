<script setup lang="ts">
import {
  getBraceImage,
  getColumnMapImage,
  getConnectionSpecimenImage,
  getDuctileFractureImage,
  getResidualStressImage,
  getSteelMaterialImage,
  getTensileCouponImage,
  getEbfImage
} from '@/utils/component'
import { testConfigurationNameMapping } from '@/utils/hss'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

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
        <li>
          {{ data.connection_type }}, {{ t('map.beam') }} {{ data.section_b }} {{ t('map.col') }}
          {{ data.section_c }}
        </li>
        <li>
          <img :alt="data.specimen_type" :src="getConnectionSpecimenImage(data.specimen_type)" />
        </li>
        <li>
          <a :href="`/connections/database?id=${data.id}&detail=true`">
            {{ t('map.view_experimental_data') }}
          </a>
        </li>
      </ul>
    </template>
    <template v-else-if="type === 'Braces'">
      <h3>
        <a target="_blank" :href="data.link"> {{ data.investigator }} ({{ data.date }}) </a>
      </h3>
      <ul>
        <li>{{ t('map.cross_section') }} {{ data.cross_section_size }}</li>
        <li>{{ t('map.kl_r') }} {{ data.kl_r }}</li>
        <li>
          <img :alt="t('map.alt_brace')" :src="getBraceImage(data.boundary_condition)" />
        </li>
        <li>
          <a :href="`/braces/database?id=${data.id}&detail=true`">
            {{ t('map.view_experimental_data') }}
          </a>
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
          {{ data.axial_lp }} (Pg/Py = {{ data.p_g_over_p_ym }}), {{ t('map.column') }}
          {{ data.section_c }}
        </li>
        <li>
          <img
            :alt="t('map.alt_column')"
            :src="getColumnMapImage(data.axis_of_bending, data.boundary_condition)"
          />
        </li>
        <li>
          <a :href="`/columns/database?id=${data.id}&detail=true`">
            {{ t('map.view_experimental_data') }}
          </a>
        </li>
      </ul>
    </template>
    <template v-else-if="type === 'Cyclic Coupons'">
      <h3>
        <a target="_blank" :href="data.link"> {{ data.experimental_program }} ({{ data.date }}) </a>
      </h3>
      <ul>
        <li>{{ t('map.profile_type') }} {{ data.profile_type }}</li>
        <li>{{ t('map.cross_section') }} {{ data.profile }}</li>
        <li>
          <img :alt="t('map.alt_material')" :src="getSteelMaterialImage()" />
        </li>
        <li>
          <a :href="`/materials/cyclic-coupons?id=${data.id}&detail=true`">
            {{ t('map.view_experimental_data') }}
          </a>
        </li>
      </ul>
    </template>
    <template v-else-if="type === 'Residual Stresses'">
      <h3>
        <a target="_blank" :href="data.link"> {{ data.experimental_program }} ({{ data.date }}) </a>
      </h3>
      <ul>
        <li>{{ t('map.profile_type') }} {{ data.profile_type }}</li>
        <li>{{ t('map.cross_section') }} {{ data.profile }}</li>
        <li>
          <img :alt="t('map.alt_residual_stress')" :src="getResidualStressImage()" />
        </li>
        <li>
          <a :href="`/residuals/database?id=${data.id}&detail=true`">
            {{ t('map.view_experimental_data') }}
          </a>
        </li>
      </ul>
    </template>
    <template v-else-if="type === 'HSS Columns'">
      <h3>
        <a target="_blank" :href="data.url"> {{ data.investigator }} ({{ data.date }}) </a>
      </h3>
      <ul>
        <li>
          {{ t('map.test_configuration') }}
          {{ testConfigurationNameMapping.get(data.test_configuration) }}
        </li>
        <li>{{ t('map.tube_section') }} {{ data.tube_section }}</li>
        <li>
          <img :alt="t('map.alt_hss_column')" src="/img/hss/hss_tooltip.png" />
        </li>
        <li>
          <a :href="`/hss-columns/database?id=${data.id}&detail=true`">
            {{ t('map.view_experimental_data') }}
          </a>
        </li>
      </ul>
    </template>
    <template v-else-if="type === 'Tensile Coupons'">
      <h3>
        <a target="_blank" :href="data.link"> {{ data.experimental_program }} ({{ data.year }}) </a>
      </h3>
      <ul>
        <li>{{ t('map.investigator') }} {{ data.investigator }}</li>
        <li>
          <img :alt="t('map.alt_tensile_coupon')" :src="getTensileCouponImage()" />
        </li>
        <li>
          <a :href="`/materials/tensile-coupons?id=${data.id}&detail=true`">
            {{ t('map.view_experimental_data') }}
          </a>
        </li>
      </ul>
    </template>
    <template v-else-if="type === 'Ductile Fracture'">
      <h3>
        <a target="_blank" :href="data.link"> {{ data.experimental_program }} ({{ data.date }}) </a>
      </h3>
      <ul>
        <li>
          <strong>{{ t('map.specimen') }}</strong> {{ data.specimen_designation }}
        </li>
        <li>
          <strong>{{ t('map.type') }}</strong> {{ data.specimen_type }}
        </li>
        <li>
          <img :alt="t('map.alt_ductile_fracture')" :src="getDuctileFractureImage()" />
        </li>
        <li>
          <a :href="`/materials/ductile-fracture?id=${data.id}&detail=true`">
            {{ t('map.view_experimental_data') }}
          </a>
        </li>
      </ul>
    </template>
    <template v-else-if="type === 'EBF Links'">
      <h3>
        <a target="_blank" :href="data.url"> {{ data.investigator }} ({{ data.year }}) </a>
      </h3>
      <ul>
        <li>
          <strong>{{ t('map.specimen_id') }}</strong> {{ data.spec_id }}
        </li>
        <li>
          <strong>{{ t('map.profile') }}</strong> {{ data.profile }}
        </li>
        <li>
          <strong>{{ t('map.link_location') }}</strong> {{ data.link_loc }}
        </li>
        <li>
          <strong>{{ t('map.link_length') }}</strong> {{ data.e }} mm
        </li>
        <li>
          <strong>{{ t('map.section_type') }}</strong> {{ data.sec_type }}
        </li>
        <li>
          <strong>{{ t('map.classification') }}</strong> {{ data.class_aisc }}
        </li>
        <li>
          <img :alt="t('map.alt_ebf_link')" :src="getEbfImage(data.l_confi)" />
        </li>
        <li>
          <a :href="`/ebf-links/database?id=${data.id}&detail=true`">
            {{ t('map.view_experimental_data') }}
          </a>
        </li>
      </ul>
    </template>
    <template v-else>
      <h3>{{ t('map.no_tooltip', { type }) }}</h3>
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
