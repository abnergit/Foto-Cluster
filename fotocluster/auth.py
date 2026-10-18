"""Proteção por senha.

Só o hash PBKDF2-SHA256 (com salt) da senha fica no código; a senha em si não.
"""

import hashlib
import hmac
import time
import tkinter as tk
from tkinter import ttk

_SALT = bytes.fromhex("28f8cc6150a91ecb75b9693aefd04487")
_HASH = bytes.fromhex("ee6e62fce1779175a33153ed9ded092b3a2807597be0a25b4e0ed46eea0db6ba")
_ITERATIONS = 300_000
MAX_ATTEMPTS = 5


def check_password(password):
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), _SALT, _ITERATIONS)
    return hmac.compare_digest(digest, _HASH)


def ask_password(root, app_name):
    """Mostra a janela de senha. Retorna True se a senha correta foi digitada."""
    result = {"ok": False, "attempts": 0}

    dlg = tk.Toplevel(root)
    dlg.title(app_name)
    dlg.resizable(False, False)
    dlg.configure(bg="#f4f5f7")
    frame = ttk.Frame(dlg, padding=24)
    frame.pack()

    ttk.Label(frame, text=app_name, font=("Segoe UI Semibold", 16)).pack(anchor="w")
    ttk.Label(frame, text="Digite a senha de acesso para continuar.",
              foreground="#6b7280").pack(anchor="w", pady=(2, 14))
    pwd = tk.StringVar()
    entry = ttk.Entry(frame, textvariable=pwd, show="•", width=32)
    entry.pack(fill="x")
    msg = tk.StringVar()
    ttk.Label(frame, textvariable=msg, foreground="#c0392b").pack(anchor="w", pady=(6, 0))

    buttons = ttk.Frame(frame)
    buttons.pack(fill="x", pady=(10, 0))

    def submit(_event=None):
        if check_password(pwd.get()):
            result["ok"] = True
            dlg.destroy()
            return
        result["attempts"] += 1
        left = MAX_ATTEMPTS - result["attempts"]
        if left <= 0:
            dlg.destroy()
            return
        time.sleep(1)  # dificulta tentativas em sequência
        pwd.set("")
        msg.set(f"Senha incorreta. {left} tentativa{'s' if left != 1 else ''} restante"
                f"{'s' if left != 1 else ''}.")

    ttk.Button(buttons, text="Sair", command=dlg.destroy).pack(side="right")
    ttk.Button(buttons, text="Entrar", command=submit).pack(side="right", padx=6)
    entry.bind("<Return>", submit)
    dlg.protocol("WM_DELETE_WINDOW", dlg.destroy)

    dlg.update_idletasks()
    x = (dlg.winfo_screenwidth() - dlg.winfo_width()) // 2
    y = (dlg.winfo_screenheight() - dlg.winfo_height()) // 3
    dlg.geometry(f"+{x}+{y}")
    dlg.attributes("-topmost", True)  # aparece na frente das outras janelas
    dlg.lift()
    dlg.after(500, lambda: dlg.attributes("-topmost", False))
    entry.focus_force()
    dlg.grab_set()
    root.wait_window(dlg)
    return result["ok"]
