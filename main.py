import os
import sys
import time
import pickle
import threading
import tkinter as tk
from tkinter import ttk, filedialog
from pynput import mouse, keyboard

class MouseKeyboardRecorderPlayer:
    def __init__(self, master):
        self.master = master
        self.master.title("Gravador e Reprodutor de Mouse e Teclado")
        self.master.resizable(False, False)

        # Inicialização de variáveis
        self.eventos = []
        self.inicio_gravacao = None
        self.rodando_reproducao = False
        self.rodando_gravacao = False
        self.velocidade_atual = 1.0
        self.loop_reproducao = tk.BooleanVar()
        self.reproduzindo = False  # Flag para indicar reprodução em andamento
        self.listener_atalhos = None  # Inicializar como None

        # Lock para sincronização
        self.lock = threading.Lock()

        # Configuração da interface
        self.create_widgets()

        # Inicialização dos controladores
        self.controller_mouse = mouse.Controller()
        self.controller_keyboard = keyboard.Controller()
        self.listener_mouse = None
        self.listener_teclado = None

        # Inicializar o listener de teclado para atalhos
        self.iniciar_listener_atalhos()

    def create_widgets(self):
        frame = ttk.Frame(self.master, padding=10)
        frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Botões de Gravação
        frame_gravacao = ttk.LabelFrame(frame, text="Gravação", padding=10)
        frame_gravacao.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        self.btn_iniciar_gravacao = ttk.Button(frame_gravacao, text="Iniciar Gravação", command=self.iniciar_gravacao)
        self.btn_iniciar_gravacao.grid(row=0, column=0, padx=5, pady=5)

        self.btn_parar_gravacao = ttk.Button(frame_gravacao, text="Parar Gravação", command=self.parar_gravacao, state='disabled')
        self.btn_parar_gravacao.grid(row=0, column=1, padx=5, pady=5)

        self.btn_salvar = ttk.Button(frame_gravacao, text="Salvar Gravação", command=self.salvar_gravacao, state='disabled')
        self.btn_salvar.grid(row=1, column=0, padx=5, pady=5)

        self.btn_carregar = ttk.Button(frame_gravacao, text="Carregar Gravação", command=self.carregar_gravacao)
        self.btn_carregar.grid(row=1, column=1, padx=5, pady=5)

        # Botões de Reprodução
        frame_reproducao = ttk.LabelFrame(frame, text="Reprodução", padding=10)
        frame_reproducao.grid(row=1, column=0, padx=5, pady=5, sticky="ew")

        self.btn_iniciar_reproducao = ttk.Button(frame_reproducao, text="Iniciar Reprodução", command=self.iniciar_reproducao, state='disabled')
        self.btn_iniciar_reproducao.grid(row=0, column=0, padx=5, pady=5)

        self.btn_parar_reproducao = ttk.Button(frame_reproducao, text="Parar Reprodução", command=self.parar_reproducao, state='disabled')
        self.btn_parar_reproducao.grid(row=0, column=1, padx=5, pady=5)

        self.check_loop = ttk.Checkbutton(frame_reproducao, text="Reprodução em Loop", variable=self.loop_reproducao)
        self.check_loop.grid(row=1, column=0, columnspan=2, padx=5, pady=5)

        # Controle de Velocidade
        frame_velocidade = ttk.LabelFrame(frame, text="Controle de Velocidade", padding=10)
        frame_velocidade.grid(row=2, column=0, padx=5, pady=5, sticky="ew")

        ttk.Label(frame_velocidade, text="Velocidade de Reprodução:").grid(row=0, column=0, padx=5, pady=5, sticky='e')

        self.label_velocidade = ttk.Label(frame_velocidade, text=f"{self.velocidade_atual:.1f}x")
        self.label_velocidade.grid(row=0, column=2, padx=5, pady=5, sticky='w')

        self.scale_velocidade = ttk.Scale(frame_velocidade, from_=0.1, to=3.0, orient='horizontal', command=self.atualizar_velocidade)
        self.scale_velocidade.set(self.velocidade_atual)
        self.scale_velocidade.grid(row=0, column=1, padx=5, pady=5, sticky='w')

        # Descrição dos Atalhos de Teclado
        descricao_atalhos = (
            "Atalhos de Teclado:\n"
            "Ctrl + Shift + R: Iniciar/Parar Gravação\n"
            "Ctrl + Shift + P: Iniciar/Parar Reprodução"
        )
        self.label_atalhos = ttk.Label(frame, text=descricao_atalhos, foreground="blue")
        self.label_atalhos.grid(row=3, column=0, padx=5, pady=10, sticky='w')

        # Barra de Progresso
        frame_progresso = ttk.Frame(frame, padding=10)
        frame_progresso.grid(row=4, column=0, padx=5, pady=5, sticky="ew")

        self.progress = ttk.Progressbar(frame_progresso, orient='horizontal', length=400, mode='determinate')
        self.progress.grid(row=0, column=0, padx=5, pady=5)

        # Barra de Status
        self.status_var = tk.StringVar()
        self.status_var.set("Pronto")
        self.status_bar = ttk.Label(frame, textvariable=self.status_var, relief='sunken', anchor='w')
        self.status_bar.grid(row=5, column=0, sticky='we', padx=5, pady=5)

    def iniciar_listener_atalhos(self):
        # Inicializar o listener de atalhos
        if self.listener_atalhos:
            self.listener_atalhos.stop()
        self.listener_atalhos = keyboard.GlobalHotKeys({
            '<ctrl>+<shift>+r': self.toggle_gravacao,
            '<ctrl>+<shift>+p': self.toggle_reproducao
        })
        self.listener_atalhos.start()

    def iniciar_gravacao(self):
        if self.rodando_gravacao or self.reproduzindo:
            return

        self.eventos = []
        self.inicio_gravacao = time.time()
        self.rodando_gravacao = True

        # Atualizar botões
        self.btn_iniciar_gravacao.config(state='disabled')
        self.btn_parar_gravacao.config(state='normal')
        self.btn_iniciar_reproducao.config(state='disabled')
        self.btn_salvar.config(state='disabled')

        # Iniciar listener de mouse
        self.listener_mouse = mouse.Listener(
            on_move=self.on_move,
            on_click=self.on_click,
            on_scroll=self.on_scroll
        )
        self.listener_mouse.start()

        # Iniciar listener de teclado
        self.listener_teclado = keyboard.Listener(
            on_press=self.on_press_key,
            on_release=self.on_release_key
        )
        self.listener_teclado.start()

        # Atualizar status
        self.status_var.set("Gravação em andamento...")

    def parar_gravacao(self):
        if not self.rodando_gravacao:
            return

        # Parar listeners
        if self.listener_mouse:
            self.listener_mouse.stop()
            self.listener_mouse = None
        if self.listener_teclado:
            self.listener_teclado.stop()
            self.listener_teclado = None

        self.rodando_gravacao = False

        # Atualizar botões
        self.btn_iniciar_gravacao.config(state='normal')
        self.btn_parar_gravacao.config(state='disabled')
        if self.eventos:
            self.btn_iniciar_reproducao.config(state='normal')
            self.btn_salvar.config(state='normal')

        # Atualizar status
        self.status_var.set(f"Gravação finalizada. {len(self.eventos)} eventos capturados.")

    def on_move(self, x, y):
        with self.lock:
            tempo = time.time() - self.inicio_gravacao
            evento = ('move', (x, y), tempo)
            self.eventos.append(evento)

    def on_click(self, x, y, button, pressed):
        with self.lock:
            tempo = time.time() - self.inicio_gravacao
            evento = ('click', (x, y, button, pressed), tempo)
            self.eventos.append(evento)

    def on_scroll(self, x, y, dx, dy):
        with self.lock:
            tempo = time.time() - self.inicio_gravacao
            evento = ('scroll', (x, y, dx, dy), tempo)
            self.eventos.append(evento)

    def on_press_key(self, key):
        with self.lock:
            tempo = time.time() - self.inicio_gravacao
            evento = ('keypress', key, tempo)
            self.eventos.append(evento)

    def on_release_key(self, key):
        with self.lock:
            tempo = time.time() - self.inicio_gravacao
            evento = ('keyrelease', key, tempo)
            self.eventos.append(evento)

    def salvar_gravacao(self):
        if not self.eventos:
            self.status_var.set("Nenhum evento para salvar.")
            return
        arquivo = filedialog.asksaveasfilename(defaultextension=".pkl", filetypes=[("Pickle files", "*.pkl")])
        if arquivo:
            try:
                with open(arquivo, 'wb') as f:
                    pickle.dump(self.eventos, f)
                self.status_var.set(f"Gravação salva em {arquivo}")
            except Exception as e:
                self.status_var.set(f"Erro ao salvar gravação: {e}")

    def carregar_gravacao(self):
        arquivo = filedialog.askopenfilename(defaultextension=".pkl", filetypes=[("Pickle files", "*.pkl")])
        if arquivo:
            try:
                with open(arquivo, 'rb') as f:
                    self.eventos = pickle.load(f)
                self.status_var.set(f"{len(self.eventos)} eventos carregados de {arquivo}")
                self.btn_iniciar_reproducao.config(state='normal')
                self.btn_salvar.config(state='normal')
            except Exception as e:
                self.status_var.set(f"Erro ao carregar gravação: {e}")

    def iniciar_reproducao(self):
        if self.rodando_reproducao or not self.eventos:
            return

        self.rodando_reproducao = True
        self.reproduzindo = True  # Ativar flag de reprodução

        # Atualizar botões
        self.btn_iniciar_reproducao.config(state='disabled')
        self.btn_parar_reproducao.config(state='normal')
        self.btn_iniciar_gravacao.config(state='disabled')

        # Resetar a barra de progresso
        self.progress['maximum'] = len(self.eventos)
        self.progress['value'] = 0

        # Atualizar status
        self.status_var.set("Reprodução em andamento...")

        # Não parar o listener de atalhos para permitir parar a reprodução via atalho

        # Iniciar thread de reprodução
        self.thread_reproducao = threading.Thread(target=self.reproduzir_eventos, daemon=True)
        self.thread_reproducao.start()

    def parar_reproducao(self):
        if not self.rodando_reproducao:
            return

        self.rodando_reproducao = False

        # Atualizar botões
        self.btn_iniciar_reproducao.config(state='normal')
        self.btn_parar_reproducao.config(state='disabled')
        self.btn_iniciar_gravacao.config(state='normal')

        # Atualizar status
        self.status_var.set("Reprodução parada.")

    def atualizar_velocidade(self, val):
        try:
            velocidade = float(val)
            if velocidade <= 0:
                velocidade = 1.0  # Prevenir velocidade zero ou negativa
            self.velocidade_atual = velocidade
            self.label_velocidade.config(text=f"{self.velocidade_atual:.1f}x")
        except ValueError:
            pass  # Ignore valores inválidos

    def reproduzir_eventos(self):
        try:
            while self.rodando_reproducao:
                prev_tempo = 0  # Tempo do evento anterior
                for idx, evento in enumerate(self.eventos):
                    if not self.rodando_reproducao:
                        break
                    tipo, dados, tempo = evento
                    # Calcula o delta de tempo entre eventos
                    delta = tempo - prev_tempo
                    prev_tempo = tempo
                    # Ajusta o tempo de espera com base na velocidade
                    espera = delta / self.velocidade_atual
                    if espera > 0:
                        time.sleep(espera)
                    # Executa o evento
                    if tipo == 'move':
                        x, y = dados
                        self.controller_mouse.position = (x, y)
                    elif tipo == 'click':
                        x, y, button, pressed = dados
                        self.controller_mouse.position = (x, y)
                        if pressed:
                            self.controller_mouse.press(button)
                        else:
                            self.controller_mouse.release(button)
                    elif tipo == 'scroll':
                        x, y, dx, dy = dados
                        self.controller_mouse.position = (x, y)
                        self.controller_mouse.scroll(dx, dy)
                    elif tipo == 'keypress':
                        self.controller_keyboard.press(dados)
                    elif tipo == 'keyrelease':
                        self.controller_keyboard.release(dados)
                    # Atualizar barra de progresso
                    self.progress['value'] = idx + 1
                    self.master.update_idletasks()
                if self.loop_reproducao.get() and self.rodando_reproducao:
                    self.progress['value'] = 0
                else:
                    break
        except Exception as e:
            self.status_var.set(f"Erro durante reprodução: {e}")
        finally:
            self.rodando_reproducao = False
            self.reproduzindo = False  # Desativar flag de reprodução
            # Reiniciar o listener de atalhos após a reprodução
            # Não é necessário reiniciar aqui, pois o listener está ativo
            self.btn_iniciar_reproducao.config(state='normal')
            self.btn_parar_reproducao.config(state='disabled')
            self.btn_iniciar_gravacao.config(state='normal')
            self.progress['value'] = 0
            if not self.loop_reproducao.get():
                self.status_var.set("Reprodução finalizada.")
            else:
                self.status_var.set("Reprodução em loop.")

    def toggle_gravacao(self):
        """
        Alterna entre iniciar e parar a gravação.
        """
        if self.rodando_reproducao:
            # Ignorar se estiver reproduzindo
            return
        if self.rodando_gravacao:
            self.parar_gravacao()
        else:
            self.iniciar_gravacao()

    def toggle_reproducao(self):
        """
        Alterna entre iniciar e parar a reprodução.
        """
        if self.rodando_reproducao:
            self.parar_reproducao()
        else:
            self.iniciar_reproducao()

    def on_closing(self):
        # Parar quaisquer listeners ou threads
        if self.rodando_gravacao:
            self.parar_gravacao()
        if self.rodando_reproducao:
            self.parar_reproducao()
        if self.listener_atalhos:
            self.listener_atalhos.stop()
        self.master.destroy()

def main():
    root = tk.Tk()
    app = MouseKeyboardRecorderPlayer(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()
