import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { Project, Contact } from '../types'

export const useAppStore = defineStore('app', () => {
  const projects = ref<Project[]>([])
  const contacts = ref<Contact[]>([])
  const contactsRefreshKey = ref(0)

  function setProjects(p: Project[]) { projects.value = p }
  function setContacts(c: Contact[]) { contacts.value = c }
  function refreshContacts() { contactsRefreshKey.value++ }

  return { projects, contacts, contactsRefreshKey, setProjects, setContacts, refreshContacts }
})
