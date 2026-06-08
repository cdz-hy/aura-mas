export interface MenuItem {
  code: string
  name: string
  path: string | null
  icon: string | null
  type: 'menu' | 'section' | 'button'
  children: MenuItem[]
}
