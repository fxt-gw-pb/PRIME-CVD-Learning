"""第3、4周：线性回归和横断面Logistic；不把随访事件直接当5年标签。"""
from __future__ import annotations
import numpy as np
import pandas as pd
import statsmodels.api as sm
from sklearn.metrics import roc_auc_score, average_precision_score, brier_score_loss, confusion_matrix


def design_basics(df):
    # 这里是事先规定的单位变换和编码，没有从全数据学习均值/插补值。
    return pd.DataFrame({"intercept":1.0,"Age_per10":df.Age/10,"BMI_per5":df.BMI/5,
                         "smoking_ex":(df.smoking_status=="ex").astype(float),
                         "smoking_current":(df.smoking_status=="current").astype(float)},index=df.index)


def run_basics(train,valid):
    X=design_basics(train); V=design_basics(valid)
    ols=sm.OLS(train.SBP,X).fit(cov_type="HC3")
    ci=ols.conf_int()
    linear=pd.DataFrame({"term":X.columns,"coefficient":ols.params.to_numpy(),
                         "ci_low":ci.iloc[:,0].to_numpy(),"ci_high":ci.iloc[:,1].to_numpy(),"p":ols.pvalues.to_numpy()})
    logistic=sm.GLM(train.diabetes,X,family=sm.families.Binomial()).fit()
    lci=logistic.conf_int(); p=logistic.predict(V).to_numpy()
    logtable=pd.DataFrame({"term":X.columns,"OR":np.exp(logistic.params.to_numpy()),
                           "ci_low":np.exp(lci.iloc[:,0].to_numpy()),"ci_high":np.exp(lci.iloc[:,1].to_numpy()),
                           "p":logistic.pvalues.to_numpy()})
    result={"task":"基线糖尿病横断面分类，非未来发病预测；阈值事先固定0.5，非临床推荐阈值。",
            "valid_AUROC":float(roc_auc_score(valid.diabetes,p)),
            "valid_AUPRC":float(average_precision_score(valid.diabetes,p)),
            "valid_prevalence":float(valid.diabetes.mean()),"valid_Brier":float(brier_score_loss(valid.diabetes,p)),
            "confusion_matrix_at_0_5":confusion_matrix(valid.diabetes,p>=.5,labels=[0,1]).tolist(),
            "linear_valid_RMSE":float(np.sqrt(np.mean((valid.SBP-ols.predict(V))**2)))}
    return linear,logtable,result
