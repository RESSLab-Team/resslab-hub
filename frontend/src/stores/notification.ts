import { defineStore } from 'pinia'

interface State {
  message: string
  url: string | undefined
}

export const useNotificationStore = defineStore('notification', {
  state: (): State => ({
    message: '',
    url: undefined
  }),
  actions: {
    notify(message: string, url?: string) {
      this.message = message
      this.url = url
    }
  }
})
