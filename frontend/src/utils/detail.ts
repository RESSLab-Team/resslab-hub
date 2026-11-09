import type { DatabaseId } from '@/utils/navigation'
import type { InjectionKey, Ref } from 'vue'

/**
 * The database of the specimen drawer, provided by `CommonDetail.vue`. A
 * `PropertyItem` with a `column` reads it to find that column in the data
 * dictionary and show its description and unit on hover.
 */
export const DETAIL_DATABASE_KEY: InjectionKey<Ref<DatabaseId | undefined>> =
  Symbol('detail-database')
