import { Routes } from '@angular/router';
import { authGuard } from './core/guards/auth.guard';
import { guestGuard } from './core/guards/guest.guard';

export const routes: Routes = [
  {
    path: 'login',
    loadComponent: () =>
      import('./features/auth/login/login.component').then((m) => m.LoginComponent),
    canActivate: [guestGuard]
  },
  {
    path: 'register',
    loadComponent: () =>
      import('./features/auth/register/register.component').then((m) => m.RegisterComponent),
    canActivate: [guestGuard]
  },
  {
    path: 'dashboard',
    loadComponent: () =>
      import('./features/dashboard/dashboard.component').then((m) => m.DashboardComponent),
    canActivate: [authGuard]
  },
  {
    path: 'profile',
    loadComponent: () =>
      import('./features/profile/profile.component').then((m) => m.ProfileComponent),
    canActivate: [authGuard]
  },
  {
    path: 'resumes',
    loadComponent: () =>
      import('./features/resumes/resumes.component').then((m) => m.ResumesComponent),
    canActivate: [authGuard]
  },
  {
    path: 'opportunities',
    loadComponent: () =>
      import('./features/coming-soon-pages/opportunities.component').then((m) => m.OpportunitiesComponent),
    canActivate: [authGuard]
  },
  {
    path: 'skill-gap',
    loadComponent: () =>
      import('./features/skill-gap/skill-gap.component').then((m) => m.SkillGapComponent),
    canActivate: [authGuard]
  },
  {
    path: 'outreach',
    loadComponent: () =>
      import('./features/outreach/outreach.component').then((m) => m.OutreachComponent),
    canActivate: [authGuard]
  },
  {
    path: 'activity',
    loadComponent: () =>
      import('./features/coming-soon-pages/activity.component').then((m) => m.ActivityComponent),
    canActivate: [authGuard]
  },
  {
    path: 'settings',
    loadComponent: () =>
      import('./features/coming-soon-pages/settings.component').then((m) => m.SettingsComponent),
    canActivate: [authGuard]
  },
  {
    path: '',
    redirectTo: 'dashboard',
    pathMatch: 'full'
  },
  {
    path: '**',
    redirectTo: 'dashboard'
  }
];
