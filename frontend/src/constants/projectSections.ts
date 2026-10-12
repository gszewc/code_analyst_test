import { ActivityIcon, FolderIcon, BarChartIcon } from 'lucide-vue-next'

export type ProjectSectionRouteName = 'project-graph' | 'project-files' | 'project-analysis'

export interface ProjectSectionMeta {
  name: 'Graph' | 'Files' | 'Analysis'
  routeName: ProjectSectionRouteName
  icon: typeof ActivityIcon
  slug: 'graph' | 'files' | 'analysis'
}

export const PROJECT_SECTIONS: ProjectSectionMeta[] = [
  { name: 'Graph', routeName: 'project-graph', icon: ActivityIcon, slug: 'graph' },
  { name: 'Files', routeName: 'project-files', icon: FolderIcon, slug: 'files' },
  { name: 'Analysis', routeName: 'project-analysis', icon: BarChartIcon, slug: 'analysis' },
]
