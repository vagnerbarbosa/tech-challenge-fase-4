module.exports = {
  extends: ['@commitlint/config-conventional'],
  rules: {
    // Tipo é obrigatório e deve ser minúsculo
    'type-enum': [
      2,
      'always',
      [
        'feat',     // Nova funcionalidade
        'fix',      // Correção de bug
        'docs',     // Documentação
        'style',    // Formatação (sem mudança de código)
        'refactor', // Refatoração de código
        'perf',     // Melhoria de performance
        'test',     // Adição/correção de testes
        'build',    // Mudanças no sistema de build
        'ci',       // Mudanças em CI/CD
        'chore',    // Outras mudanças
        'revert',   // Reverte um commit anterior
      ],
    ],
    'type-case': [2, 'always', 'lower-case'],
    'type-empty': [2, 'never'],

    // Escopo é opcional mas deve ser minúsculo se presente
    'scope-case': [2, 'always', 'lower-case'],

    // Descrição é obrigatória
    'subject-empty': [2, 'never'],
    'subject-case': [0], // Desabilita validação de case para português

    // Cabeçalho não pode ter mais de 100 caracteres
    'header-max-length': [2, 'always', 100],

    // Corpo e rodapé são opcionais
    'body-leading-blank': [1, 'always'],
    'footer-leading-blank': [1, 'always'],

    // Aumenta limite de caracteres no corpo do commit (padrão é 100)
    'body-max-line-length': [2, 'always', 200],
  },
};
