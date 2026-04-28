<script setup lang="ts">
import { TensileCouponField, type TensileCouponModel } from '@/backend'
import TensileCouponTable from '@/components/tensile-coupons/TensileCouponTable.vue'

import { useDashboard } from '@/composables/dashboard'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()
const { clickTableRow, item, query, search, searches, updatePage } =
  useDashboard<TensileCouponModel>(route, router, TensileCouponField)
</script>

<template>
  <v-row>
    <v-col md="6">
      <v-row>
        <v-col cols="12">
          <tensile-coupon-table
            v-model:search="search"
            v-model:searches="searches"
            :query="query"
            @click:row="clickTableRow"
            @update:page="updatePage"
          />
        </v-col>
      </v-row>
    </v-col>
    <v-col md="6">
      <v-row v-if="item">
        <v-col cols="12">
          <!-- Detail panel added in Commit 7 -->
        </v-col>
      </v-row>
    </v-col>
  </v-row>
</template>
