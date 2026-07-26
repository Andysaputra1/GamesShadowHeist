import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-game',
  standalone: true,
  imports: [RouterLink],
  templateUrl: './game.html',
  styleUrl: './game.css'
})
export class Game {
  playerMessage: string | null = null;
  npcMessage: string | null = null; 

  sendMessage(text: string) {
    if (!text || text.trim() === '') return;
    this.playerMessage = text;
    setTimeout(() => {
      this.playerMessage = null;
    }, 4000);
  }
}