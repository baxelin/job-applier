"""Telas do modal da Candidatura Simplificada, reduzidas do HTML real (out/2026) e com dados fictícios."""


def modal(body: str, buttons: tuple[str, ...] = ("Avançar",), progress: str | None = "1 de 3 páginas") -> str:
    progress_line = f"<div>33 por cento concluído</div><p>{progress}</p>" if progress else ""
    footer = "".join(f'<button type="button"><span><span>{label}</span></span></button>' for label in buttons)
    return f"""
    <dialog data-testid="dialog" open aria-labelledby="dialog-header">
      <button aria-label="Fechar" type="button"><span></span></button>
      <div>
        <header id="dialog-header"><h2>Candidate-se à empresa Empresa X</h2></header>
        <div data-testid="dialog-content">
          {progress_line}
          <div data-testid="lazy-column"><div>{body}</div></div>
          <footer>{footer}</footer>
        </div>
      </div>
      <section><h2 data-testid="toasts-title">0 notificação</h2></section>
    </dialog>
    """


def labeled_input(
    question: str, control: str = "_r_1_", value: str = "", input_type: str = "text", required: bool = True
) -> str:
    star = "*" if required else ""
    mark = "required" if required else ""
    return f"""
    <div>
      <label for="{control}"><div>{question}{star}</div></label>
      <div><input aria-describedby="{control}-info" dir="auto" id="{control}" {mark} type="{input_type}"
                  value="{value}" data-live-value="{value}"></div>
      <div data-testid="text-input-helper-text" id="{control}-info"><div><p aria-live="polite">
        <span aria-hidden="true">{len(value)}/100</span><span>{len(value)} de 100 caracteres</span>
      </p></div></div>
    </div>
    """


def question_input(question: str, control: str = "_r_2_", value: str = "", limit: int = 20) -> str:
    return f"""
    <div>
      <p>{question}*</p>
      <div>
        <div><input aria-describedby="{control}-info" aria-label="{question}" dir="auto" id="{control}" required
                    type="text" value="{value}" data-live-value="{value}"></div>
        <div data-testid="text-input-helper-text" id="{control}-info"><div><p aria-live="polite">
          <span aria-hidden="true">{len(value)}/{limit}</span><span>{len(value)} de {limit} caracteres</span>
        </p></div></div>
      </div>
    </div>
    """


def question_textarea(question: str, control: str = "_r_3_", required: bool = True) -> str:
    star = "*" if required else ""
    mark = "required" if required else ""
    return f"""
    <div>
      <p>{question}{star}</p>
      <div><textarea aria-label="{question}" dir="auto" id="{control}" {mark} rows="4" data-live-value=""></textarea></div>
    </div>
    """


def select_field(question: str, control: str, options: dict[str, str], selected: str = "") -> str:
    entries = "".join(f'<option value="{value}">{label}</option>' for value, label in options.items())
    return f"""
    <div>
      <label for="{control}"><div>{question}*</div></label>
      <div><select id="{control}" required data-live-value="{selected}">
        <option disabled hidden value=""></option>{entries}
      </select></div>
    </div>
    """


def radio_group(question: str, options: dict[str, str], checked: str | None = None) -> str:
    radios = "".join(
        f"""
        <div aria-checked="{"true" if control == checked else "false"}" aria-label="{question}" role="radio" tabindex="0">
          <div>
            <div>
              <input id="{control}" name="radio-group" type="radio"
                     data-live-checked="{"true" if control == checked else "false"}">
              <label for="{control}"></label>
            </div>
            <div><p>{label}</p></div>
          </div>
        </div>
        """
        for control, label in options.items()
    )
    return f"""
    <div>
      <p>{question}*</p>
      <fieldset aria-describedby="error-message-_r_9_" role="radiogroup"><div>{radios}</div></fieldset>
    </div>
    """


def checkbox_group(question: str, options: dict[str, str]) -> str:
    boxes = "".join(
        f"""
        <div aria-checked="false" role="checkbox" tabindex="0">
          <div>
            <div>
              <input id="{control}" tabindex="-1" type="checkbox" data-live-checked="false">
              <label for="{control}"></label>
            </div>
            <p>{label}</p>
          </div>
        </div>
        """
        for control, label in options.items()
    )
    return f"""
    <div>
      <p>{question}*</p>
      <fieldset aria-describedby="error-message-_r_8_"><div>{boxes}</div></fieldset>
    </div>
    """


def resume_radio(name: str, control: str, checked: bool, wrapped: bool) -> str:
    """Parte das vagas traz o nome do arquivo num wrapper [role=radio]; as outras, no próprio input."""
    state = "true" if checked else "false"
    radio = f'id="{control}" name="radio-group-resume" type="radio" data-live-checked="{state}"'
    radio += " checked" if checked else ""
    if wrapped:
        return f"""
        <div aria-checked="{state}" aria-label="{name}" role="radio" tabindex="0">
          <div aria-label="{name}">
            <input {radio}>
            <label for="{control}"></label>
          </div>
        </div>
        """
    return f"""
    <div><div aria-label="{name}">
      <input aria-label="{name}" {radio}>
      <label for="{control}"></label>
    </div></div>
    """


def resume_step(
    selected: str = "CV antigo.pdf", wrapped: bool = True, files: dict[str, str] | None = None
) -> str:
    files = files or {"CV antigo.pdf": "_r_11_", "CV mais antigo.pdf": "_r_12_"}
    entries = "".join(
        f"""
        <div>
          <div role="button" tabindex="0"><p>PDF</p><p><span>{name}</span></p><p>23/09/2026</p></div>
          {resume_radio(name, control, name == selected, wrapped)}
        </div>
        """
        for name, control in files.items()
    )
    return f"""
    <div>
      <p>Resume*</p>
      <p>Selecione ou carregue um currículo no formato DOC, DOCX ou PDF com menos de 2 MB</p>
    </div>
    <fieldset aria-describedby="error-message-_r_10_" role="radiogroup">{entries}</fieldset>
    <button type="button"><span>Carregar currículo</span></button>
    """


def follow_company_checkbox() -> str:
    return """
    <div>
      <input aria-label="Siga a empresa X para ficar por dentro das novidades" checked id="_r_28_" type="checkbox"
             data-live-checked="true">
      <label for="_r_28_"></label>
      <p>Siga a empresa X para ficar por dentro das novidades</p>
    </div>
    """
