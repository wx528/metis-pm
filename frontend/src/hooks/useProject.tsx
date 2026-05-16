import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from "react";
import { projectsApi, type Project } from "../api/projects";

interface ProjectContextType {
  currentProject: Project | null;
  projects: Project[];
  setCurrentProject: (project: Project | null) => void;
  refreshProjects: () => Promise<void>;
  loading: boolean;
}

const ProjectContext = createContext<ProjectContextType>({
  currentProject: null,
  projects: [],
  setCurrentProject: () => {},
  refreshProjects: async () => {},
  loading: true,
});

export function ProjectProvider({ children }: { children: ReactNode }) {
  const [currentProject, setCurrentProjectState] = useState<Project | null>(() => {
    const saved = localStorage.getItem("currentProject");
    return saved ? JSON.parse(saved) : null;
  });
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);

  const refreshProjects = useCallback(async () => {
    try {
      const data = await projectsApi.list();
      setProjects(data);
      // 如果没有当前项目，选择 default 或第一个
      if (!currentProject && data.length > 0) {
        const savedSlug = localStorage.getItem("currentProjectSlug");
        const target = savedSlug
          ? data.find((p) => p.slug === savedSlug)
          : data.find((p) => p.slug === "default") || data[0];
        if (target) {
          setCurrentProjectState(target);
          localStorage.setItem("currentProject", JSON.stringify(target));
          localStorage.setItem("currentProjectSlug", target.slug);
        }
      }
    } catch {
      // 未登录或其他错误，忽略
    } finally {
      setLoading(false);
    }
  }, [currentProject]);

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (token) {
      refreshProjects();
    } else {
      setLoading(false);
    }
  }, []);

  const setCurrentProject = useCallback((project: Project | null) => {
    setCurrentProjectState(project);
    if (project) {
      localStorage.setItem("currentProject", JSON.stringify(project));
      localStorage.setItem("currentProjectSlug", project.slug);
    } else {
      localStorage.removeItem("currentProject");
      localStorage.removeItem("currentProjectSlug");
    }
  }, []);

  return (
    <ProjectContext.Provider value={{ currentProject, projects, setCurrentProject, refreshProjects, loading }}>
      {children}
    </ProjectContext.Provider>
  );
}

export function useProject() {
  return useContext(ProjectContext);
}
