import { Routes } from '@angular/router';

import { MainPage } from './features/main-page/main-page';
import { Auth } from './features/auth/auth';
import { Lobby } from './features/lobby/lobby';
import { Game } from './features/game/game';

export const routes: Routes = [
  { path: '', redirectTo :'/login', pathMatch: 'full' },
  { path: 'login', component: Auth },
  { path: 'main', component: MainPage },
  { path: 'lobby', component: Lobby },
  { path: 'game', component: Game },
  { path: '**', redirectTo: '/login' }
];
