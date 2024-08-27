library(tidyr)
library(dplyr)
library(ggplot2)
library(data.table)
library(lme4)
library(lmerTest)

setwd('/shared/3/projects/style-influence/')
plot_dir = 'results/figures/'
data_dir = 'results/data_tables/'
reg_dir = 'results/reg_models/'

load("reg_models.RData")
seeds <- as.integer(readLines('data/random_seeds.csv'))


# Test LSM at different values of a covariate (interaction)
get_lsm_estimates <- function(df, marker, vname, seed = 1,
                              fmla = mixed_mod_equation, fmla_eff = mixed_mod_equation_cat,
                              n_sample_reg = 1000000, n_sample = 100000, n_rep = 10, re_min = 30,
                              save_outputs = TRUE){
    set.seed(seeds[seed])
    
    # Make data for plot: get LSM effect in different parameter spaces
    b <- c()
    V <- c()
    for(v in levels(df$category)){
        #message(paste(Sys.time(), v))
        sub = df %>% filter(!is.na(category) & category==v)
        if(nrow(sub)>100){
            for(ind in 1:n_rep){
                mod <- lmer(fmla, 
                            sub %>% 
                                sample_n(min(nrow(sub),n_sample), replace=T) %>% 
                                group_by(subreddit) %>% 
                                mutate(n = n()) %>%
                                ungroup() %>%
                                mutate(subreddit_re = ifelse(n >= re_min, subreddit, 'other'))
                           )
                b <- c(b, fixef(mod)['parent_style']) #fixef(mod)['parent_style'] = LSM
                V <- c(V, v) #v = region of the parameter space
            }
        }
    }
    plot_df = data.frame(variable=as.numeric(as.character(V)), lsm=b)
    if(save_outputs) fwrite(plot_df, paste0(data_dir,marker,'_',vname,'.csv'), row.names=F)
    
    # Test effect using interaction model
    if(save_outputs){
        mod <- lmer(fmla_eff, df %>% sample_n(min(nrow(df), n_sample_reg)))
        saveRDS(mod, paste0(reg_dir, marker,'_',vname,'.RDS'))
    }
    
    plot_df
}


# Test LSM at different values of two covariates (2-way interaction)
get_lsm_estimates_category <- function(df, marker, vname, cname, seed = 1,
                                       fmla = mixed_mod_equation, fmla_eff = mixed_mod_equation_cat, 
                                       fmla_eff_all = mixed_mod_equation_cat2,
                                       n_sample_reg = 1000000, n_sample = 100000, n_rep = 10, re_min = 30,
                                       save_outputs = TRUE){
    
    # Make data for plot: get LSM effect in different parameter spaces for each value of category2
    plot_df <- data.frame()
    for(c in unique(df$category2)){
        #message(paste(Sys.time(),c))
        sub_df <- get_lsm_estimates(df %>% filter(category2==c), 
                                     marker=marker, vname=paste0(vname,'_',cname), seed=seed,
                                     fmla=fmla, fmla_eff=fmla_eff, 
                                     n_sample_reg=n_sample_reg, n_sample=n_sample, n_rep=n_rep, re_min=re_min,
                                     save_outputs = FALSE)
        sub_df$category <- c
        plot_df <- rbind(plot_df, sub_df)
    }
    if(save_outputs) fwrite(plot_df, paste0(data_dir,marker,'_',vname,'_',cname,'.csv'), row.names=F)

    # Test effect using 2-level interaction model
    if(save_outputs){
        set.seed(seeds[seed])
        cats <- unique(df$category2)
        sub <- rbindlist(lapply(cats, function(c) df %>% filter(category2==c) %>% 
                                                        sample_n(min(nrow(.),as.integer(n_sample_reg/length(cats))))))
        mod <- lmer(fmla_eff_all, sub)
        saveRDS(mod, paste0(reg_dir, marker,'_',vname,'_',cname,'.RDS'))
    }
    
    plot_df
}


# Plot LSM at different parts of the parameter space
make_lsm_effect_plot <- function(marker, vname, x_label, cname='', extra_args = theme(),
                                 sp = 1, text_size = 40, plt_w = 9, plt_h = 6,
                                 line_method = '', line_colors = c(), pt_trans=0.4, xlim=c(), ylim=c(),
                                 legend_loc = 'none'){
    plot_df = fread(paste0(data_dir,marker,'_',vname,ifelse(cname=='','',paste0('_',cname)),'.csv'))
    if(length(setdiff(plot_df$category,c('Yes','No')))==0) plot_df$category <- factor(plot_df$category, levels=c('Yes','No'))
    
    n = 'style'
    if(marker == 'function') n <- '# function words'
    if(marker == 'formality') n <- 'formality'

    line_args <- geom_smooth(span = sp)
    if(line_method != "") line_args <- geom_smooth(method=line_method, span = sp)
    
    xlim_args <- scale_x_continuous()
    if(length(xlim) != 0) xlim_args <- scale_x_continuous(limits=xlim)
    
    ylim_args <- scale_y_continuous()
    if(length(ylim) != 0) ylim_args <- scale_y_continuous(limits=ylim)
    
    plot_params <- ggplot(plot_df, aes(x = variable, y = lsm)) + labs(color='')
    if(cname!='') plot_params <- ggplot(plot_df, aes(x = variable, y = lsm, color=category)) + 
                                        labs(color='Controversial') +
                                        guides(color=guide_legend(size=35, override.aes = list(size=7,fill='transparent')))
    
    options(repr.plot.width = plt_w, repr.plot.height = plt_h)
    plt <- plot_params +
            geom_point(alpha=pt_trans) +
            line_args +
            xlim_args + ylim_args +
            labs(x = x_label, y = paste0('Accommodation\n(',n,')')) +
            theme_classic() +
            theme(legend.position=legend_loc,
                  text = element_text(size = text_size)) +
            extra_args
    ggsave(paste0(plot_dir,marker,'_',vname,ifelse(cname=='','',paste0('_',cname)),'.pdf'), width = plt_w, height = plt_h)
    
    plt
}
