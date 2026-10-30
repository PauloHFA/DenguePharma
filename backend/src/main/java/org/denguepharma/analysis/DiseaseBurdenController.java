package org.denguepharma.analysis;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.Map;

/**
 * Endpoint publico para dados de Carga Global de Doenca (Eixo C - GBD / DATASUS)
 * e mapeamento de desertos de pesquisa clinica (incidencia vs ensaios realizados).
 */
@RestController
@RequestMapping("/api/public")
public class DiseaseBurdenController {

    public record DiseaseBurdenDTO(
            String countryCode,
            String countryName,
            String region,
            long estimatedCasesPerYear,
            double dalysRatePer100k,
            String predominantSerotypes,
            int clinicalTrialsCount,
            boolean isResearchDesert,
            String notice
    ) {}

    private static final List<DiseaseBurdenDTO> BURDEN_DATA = List.of(
            new DiseaseBurdenDTO(
                    "BRA", "Brasil", "America Latina / Caribe", 2900000L, 412.5, "DENV-1, DENV-2, DENV-3", 14, false,
                    "Elevada transmissao endemica com centros ativos de pesquisa em dengue."
            ),
            new DiseaseBurdenDTO(
                    "BGD", "Bangladesh", "Sudeste Asiatico", 320000L, 520.1, "DENV-2, DENV-3", 1, true,
                    "Deserto de pesquisa clinica: altissima mortalidade e DALYs com baixissima presenca de ensaios farmacologicos."
            ),
            new DiseaseBurdenDTO(
                    "VNM", "Vietna", "Sudeste Asiatico", 280000L, 385.0, "DENV-1, DENV-2, DENV-4", 11, false,
                    "Centro de pesquisa estabelecido (Hospital for Tropical Diseases / OUCRU)."
            ),
            new DiseaseBurdenDTO(
                    "IDN", "Indonesia", "Sudeste Asiatico", 140000L, 310.2, "DENV-1, DENV-2, DENV-3, DENV-4", 2, true,
                    "Deserto relativo de pesquisa: hiperendemicidade com escassos ensaios randomizados registrados."
            ),
            new DiseaseBurdenDTO(
                    "IND", "India", "Sudeste Asiatico", 4500000L, 620.8, "DENV-1, DENV-2", 4, true,
                    "Deserto severo de pesquisa: maior volume global de casos e DALYs em contraste com ensaios primarios publicados."
            ),
            new DiseaseBurdenDTO(
                    "COL", "Colombia", "America Latina / Caribe", 110000L, 290.4, "DENV-1, DENV-2", 5, false,
                    "Estudos multicentricos latino-americanos presentes."
            ),
            new DiseaseBurdenDTO(
                    "SGP", "Cingapura", "Sudeste Asiatico", 32000L, 65.0, "DENV-1, DENV-2, DENV-3", 9, false,
                    "Centro de alta renda com elevada densidade de ensaios clinicos e vigilancia genomica."
            )
    );

    @GetMapping("/disease-burden")
    public Map<String, Object> getDiseaseBurden(@RequestParam(required = false) String region,
                                                @RequestParam(required = false) Boolean desertsOnly) {
        List<DiseaseBurdenDTO> filtered = BURDEN_DATA.stream()
                .filter(d -> region == null || region.isBlank() || d.region().toLowerCase().contains(region.toLowerCase().trim()))
                .filter(d -> desertsOnly == null || !desertsOnly || d.isResearchDesert())
                .toList();

        long totalCases = filtered.stream().mapToLong(DiseaseBurdenDTO::estimatedCasesPerYear).sum();
        long totalTrials = filtered.stream().mapToInt(DiseaseBurdenDTO::clinicalTrialsCount).sum();

        return Map.of(
                "axis", "C",
                "title", "Carga de Doenca e Desertos de Pesquisa Clinica (Eixo C - GBD / OMS / DATASUS)",
                "methodologicalNotice", "A correlacao geografica de DALYs e ensaios clinicos visa identificar disparidades globais de investimento terapeutico. Nao substitui avaliacoes epidemiologicas locais (Regra RC-01).",
                "summary", Map.of(
                        "countriesCount", filtered.size(),
                        "totalEstimatedCases", totalCases,
                        "totalClinicalTrials", totalTrials,
                        "researchDesertsCount", filtered.stream().filter(DiseaseBurdenDTO::isResearchDesert).count()
                ),
                "data", filtered
        );
    }
}
