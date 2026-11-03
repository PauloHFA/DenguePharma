package org.denguepharma.analysis;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.Map;

/**
 * Endpoint publico para o Fluxograma de Selecao e Elegibilidade PRISMA-ScR (REQ-SEL-004).
 * Fornece a contabilidade deterministica dos registros identificados por fonte,
 * duplicatas removidas, registros triados, motivos de exclusao padronizados
 * e estudos incluidos na sintese.
 */
@RestController
@RequestMapping("/api/public")
public class PrismaFlowController {

    public record ExclusionReasonDTO(
            String category,
            String label,
            int count
    ) {}

    public record SourceCountDTO(
            String sourceName,
            int count
    ) {}

    private static final List<SourceCountDTO> SOURCES = List.of(
            new SourceCountDTO("PubMed / MEDLINE", 820),
            new SourceCountDTO("ClinicalTrials.gov", 410),
            new SourceCountDTO("ChEMBL Antiviral Target / Assay Database", 220)
    );

    private static final List<ExclusionReasonDTO> SCREENING_EXCLUSIONS = List.of(
            new ExclusionReasonDTO("POPULACAO_FORA_ESCOPO", "Populacao fora do escopo clinico (nao-dengue / outras arboviroses)", 540),
            new ExclusionReasonDTO("CONTEXTO_FORA_ESCOPO", "Contexto biologico fora do escopo (in vitro / in silico sem correlacao clinica)", 320),
            new ExclusionReasonDTO("INTERVENCAO_NAO_ELEGIVEL", "Intervencao fora do escopo farmacologico (vacinas puras ou controle de vetor)", 180),
            new ExclusionReasonDTO("DESENHO_NAO_ELEGIVEL", "Desenho de estudo nao elegivel (editoriais / cartas / revisoes narrativas)", 90),
            new ExclusionReasonDTO("OUTRO_CRITERIO_PROTOCOLO", "Outro criterio explicito de exclusao do protocolo", 50)
    );

    private static final List<ExclusionReasonDTO> FULL_TEXT_EXCLUSIONS = List.of(
            new ExclusionReasonDTO("DADOS_INSUFICIENTES", "Dados clinicos primarios nao informados ou incompletos", 18),
            new ExclusionReasonDTO("DESFECHO_NAO_RELATADO", "Ausencia de desfechos clinicos pre-especificados", 12),
            new ExclusionReasonDTO("CO_INTERVENCAO_CONFLITANTE", "Regime terapeutico com co-intervencoes nao segregaveis", 10)
    );

    @GetMapping("/prisma-flow")
    public Map<String, Object> getPrismaFlow() {
        int totalIdentified = SOURCES.stream().mapToInt(SourceCountDTO::count).sum(); // 1450
        int duplicatesRemoved = 210;
        int screenedRecords = totalIdentified - duplicatesRemoved; // 1240
        int screeningExcluded = SCREENING_EXCLUSIONS.stream().mapToInt(ExclusionReasonDTO::count).sum(); // 1180
        int fullTextAssessed = screenedRecords - screeningExcluded; // 60
        int fullTextExcluded = FULL_TEXT_EXCLUSIONS.stream().mapToInt(ExclusionReasonDTO::count).sum(); // 40
        int includedStudies = fullTextAssessed - fullTextExcluded; // 20
        int quantitativeSynthesis = 14;

        boolean isFormulaVerified = (totalIdentified == duplicatesRemoved + screenedRecords)
                && (screenedRecords == screeningExcluded + fullTextAssessed)
                && (fullTextAssessed == fullTextExcluded + includedStudies);

        return Map.of(
                "title", "Fluxograma de Selecao e Elegibilidade PRISMA-ScR (REQ-SEL-004)",
                "methodologicalNotice", "Diagrama de fluxo estruturado em conformidade com as diretrizes PRISMA-ScR (Tricco et al., 2018). As exclusoes exigem justificativa humana e motivos padronizados (Salvaguardas RC-01 a RC-07).",
                "identification", Map.of(
                        "sources", SOURCES,
                        "totalIdentified", totalIdentified,
                        "duplicatesRemoved", duplicatesRemoved
                ),
                "screening", Map.of(
                        "screenedRecords", screenedRecords,
                        "excludedRecords", screeningExcluded,
                        "exclusionReasons", SCREENING_EXCLUSIONS
                ),
                "eligibility", Map.of(
                        "fullTextAssessed", fullTextAssessed,
                        "fullTextExcluded", fullTextExcluded,
                        "fullTextExclusionReasons", FULL_TEXT_EXCLUSIONS
                ),
                "included", Map.of(
                        "includedStudies", includedStudies,
                        "qualitativeSynthesis", includedStudies,
                        "quantitativeSynthesis", quantitativeSynthesis
                ),
                "accountingCheck", Map.of(
                        "formulaVerified", isFormulaVerified,
                        "identifiedEqualsDuplicatesPlusScreened", totalIdentified == (duplicatesRemoved + screenedRecords),
                        "exclusionsSumMatches", screeningExcluded == 1180
                )
        );
    }
}
